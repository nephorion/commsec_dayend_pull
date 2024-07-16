import os
import time
import logging
import json
import pandas as pd
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from google.cloud import storage
from google.cloud import secretmanager
from google.cloud import pubsub_v1
from google.cloud import bigquery
from flask import Flask, jsonify, make_response
from datetime import datetime, timedelta
from commsec_download import login, download, get_browser, goto_download, close_browser

# Constants
#
file_template = '%Y%m%d'
app_name = "commsec_dayend_pull"
field_names = ['tkr','date','open','high','low','close','volume']

# Get the environment variables
#
bucket_name = os.getenv('BUCKET')
topic_name = os.getenv('TOPIC')
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

# Setup logging
#
client = google.cloud.logging.Client()
client.setup_logging()
logger = logging.getLogger(app_name)
logger.setLevel(logging.INFO)
handler = CloudLoggingHandler(client)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

logger.info(f"BUCKET = [{bucket_name}]")
logger.info(f"TOPIC = [{topic_name}]")
logger.info(f"GOOGLE_CLOUD_PROJECT = [{project_id}]")



# Setup Flask
# pylint: disable=C0103
app = Flask(__name__)

def list_files_with_prefix(bucket, prefix):
    blobs = bucket.list_blobs(prefix=prefix)
    file_list = [blob.name for blob in blobs]
    return file_list


def make_file_name(prefix, date):
    return f"{prefix}ASXEQUITIESStockEasy-{date.strftime(file_template)}.txt"


def file_exists_in_bucket(bucket, date):
    blob = bucket.blob(make_file_name('eod/',date))
    return blob.exists()

def get_secret(secrets_client, project_id, secret):
    name = f"projects/{project_id}/secrets/{secret}/versions/latest"
    secret = secrets_client.access_secret_version(request={"name": name})
    return secret.payload.data.decode("UTF-8")


def publish(publisher, topic_path, data):
    data_str = json.dumps(data)
    data_bytes = data_str.encode('utf-8')
    try:
        future = publisher.publish(topic_path, data=data_bytes)
        future.result()
        logger.info(f"Published to pub/sub")
        return True
    except Exception as e:
        logger.error(f"Unable to publish to pub/sub [{e}]")
        return False


def parse_date_str(date_str):
    retval = None
    if date_str == 'today':
        retval = datetime.now().date()
    elif date_str == 'yesterday':
        retval = datetime.now().date() - timedelta(days=1)
    else:
        retval = datetime.strptime(date_str, file_template)
    logger.info(f"--->{retval}")
    return retval

def get_date_range(from_date_str, to_date_str):
    from_date = parse_date_str(from_date_str)
    to_date = parse_date_str(to_date_str)
    date_range = pd.date_range(start=to_date, end=from_date)
    dates = date_range.tolist()
    dates.reverse()
    return dates

def get_dates_from_holiday_csv(bq_client):
    query = """
        SELECT distinct(Date) as date
        FROM `lookup.holidays`
    """
    rows = bq_client.query_and_wait(query)
    dates = [str(row["date"]) for row in rows]
    return dates

def get_filenames_in_bq(bq_client):
    query = """
        SELECT distinct(filename) as filename
        FROM `data.raw_eod`
    """
    rows = bq_client.query_and_wait(query)
    filenames = [row["filename"] for row in rows]
    return filenames

def delete_records_in_bq(bq_client,filenames):
    # Delete records in BigQuery that are not in GCS
    for filename in filenames:
        delete_query = f"""
            DELETE FROM `data.raw_eod`
            WHERE filename = '{filename}'
        """
        delete_job = bq_client.query(delete_query)
        delete_job.result()  # Wait for the job to complete

def sync_gcs_to_bq(gcs_files, bq_files, bucket, bq_client):
    files_to_insert = set(gcs_files) - set(bq_files)
    #files_to_delete = set(bq_files) - set(gcs_files)

    for file_name in files_to_insert:
        blob = bucket.blob(file_name)
        file_contents = blob.download_as_text()

        rows = file_contents.strip().split('\n')
        json_data = []
        for row in rows:
            columns = row.split(',')
            json_record = {f"{field_names[i]}": value for i, value in enumerate(columns)}
            json_record['date'] = str(datetime.strptime(json_record['date'], '%Y%m%d').date())
            json_record['filename'] = file_name
            json_record['timestamp'] = datetime.now().isoformat()
            json_data.append(json_record)

        table_ref = bq_client.dataset('data').table('raw_eod')
        errors = bq_client.insert_rows_json(table_ref, json_data)

        if errors:
            logger.error(f"Encountered errors while inserting rows for {file_name}: {errors[0]}")
        else:
            logger.info(f"Inserted rows from [{file_name}]")

    #delete_records_in_bq(bq_client, files_to_delete)


def wait_for_file(filepath, timeout):
    start_time = time.time()

    while time.time() - start_time < timeout:
        if os.path.exists(filepath):
            return True
        time.sleep(.5)

    return False

def process_date(browser, bucket, date, holidays):
    date_str = date.strftime(file_template)
    file_name = make_file_name('eod/',date)
    local_file_name = make_file_name('', date)

    if date.weekday() >= 5:
        logger.info(f"Skipped Downloading(Weekend) - {date_str}")
        return False

    if date_str in holidays:
        logger.info(f"Skipped Downloading(Holiday) - {date_str}")
        return False

    if not file_exists_in_bucket(bucket, date):
        try:
            download(browser, date)
            if not wait_for_file(local_file_name, 10):
                raise Exception(f"Error Downloading (Local Copy) - {date_str}")
            bucket.blob(file_name).upload_from_filename(local_file_name)
            logger.info(f"Uploaded - {date_str}")
        except Exception as e:
            logger.error(e)
        finally:
            if os.path.exists(local_file_name):
                os.remove(f"./{local_file_name}")
    else:
        logger.info(f"Skipped Downloading (Existing) - {date_str}")


def get_eod_data(dates):
    browser = None
    try:
        secrets_client = secretmanager.SecretManagerServiceClient()
        publisher = pubsub_v1.PublisherClient()
        bq_client = bigquery.Client()
        storage_client = storage.Client()

        commsec_user = get_secret(secrets_client, project_id, 'COMMSEC_USER')
        commsec_password = get_secret(secrets_client, project_id, 'COMMSEC_PASSWORD')

        topic_path = publisher.topic_path(project_id, topic_name)
        bucket = storage_client.bucket(bucket_name)
        holidays = get_dates_from_holiday_csv(bq_client)

        browser = get_browser('/app', headless=True)
        login(browser, commsec_user, commsec_password)
        goto_download(browser)

        for date in dates:
            process_date(
                browser,
                bucket,
                date,
                holidays
            )

        gcs_files = list_files_with_prefix(bucket, 'eod/')
        bq_files = get_filenames_in_bq(bq_client)
        sync_gcs_to_bq(gcs_files, bq_files, bucket, bq_client)

        publish(publisher, topic_path, {})
    except Exception as e:
        logger.error(f"Failed to get eod data [{e}]")
    finally:
        if browser is not None:
            close_browser(browser)


@app.route('/')
def home():
    logger.info('This is an info log message')
    return f"processing..."


@app.route('/backfill/at/<at_date_str>')
def backfill_date(at_date_str):
    dates = get_date_range(at_date_str, at_date_str)
    get_eod_data(dates)
    return make_response(jsonify({"dates":dates}), 200)


@app.route('/backfill/from/<from_date_str>/to/<to_date_str>')
def backfill(from_date_str, to_date_str):
    dates = get_date_range(from_date_str, to_date_str)
    get_eod_data(dates)
    return make_response(jsonify({"dates":dates}), 200)


if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
