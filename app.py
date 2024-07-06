import os
from enum import Enum
import logging
import json
import pandas as pd
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from google.cloud import storage
from google.cloud import secretmanager
from google.cloud import pubsub_v1
from flask import Flask
from datetime import datetime
from commsec_download import login, download, get_browser, goto_download, close_browser

bucket_name = os.getenv('BUCKET')
topic_name = os.getenv('TOPIC')
commsec_user = os.getenv('COMMSEC_USER')
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

# pylint: disable=C0103
app = Flask(__name__)

file_template = '%Y%m%d'


def setup_logging():
    client = google.cloud.logging.Client()
    client.setup_logging()

    # Configure logging
    logger = logging.getLogger('cloudLogger')
    logger.setLevel(logging.INFO)

    # Create a Cloud Logging handler
    handler = CloudLoggingHandler(client)
    handler.setLevel(logging.INFO)

    # Add the handler to the logger
    logger.addHandler(handler)

    # Optional: add a console handler for local development
    return logger


logger = setup_logging()


def get_files_in_bucket(storage_client, bucket):
    blobs = bucket.list_blobs()
    file_list = [blob.name for blob in blobs]
    return file_list


def make_file_name(date):
    return f"ASXEQUITIESStockEasy-{date.strftime(file_template)}.txt"


def file_exists_in_bucket(bucket, date):
    blob = bucket.blob(make_file_name(date))
    return blob.exists()


Status = Enum('Status', 'SUCCESS ERROR SKIPPED_WEEKEND SKIPPED_HOLIDAY SKIPPED_EXISTS')


def make_status(date, status: Status, msg):
    return {
        'date': date.strftime(file_template),
        'status': status.name,
        'code': status.value,
        'msg': msg
    }


def process_date(browser, bucket, date, holidays):
    date_str = date.strftime(file_template)
    file_name = make_file_name(date)

    if date.weekday() >= 5:
        return make_status(
            date,
            Status.SKIPPED_WEEKEND,
            f"Skipped Downloading(Weekend) - {date_str}"
        )

    if date_str in holidays:
        return make_status(
            date,
            Status.SKIPPED_HOLIDAY,
            f"Skipped Downloading(Holiday) - {date_str}"
        )

    if not file_exists_in_bucket(bucket, date):
        if not download(browser, date):
            return make_status(
                date,
                Status.ERROR,
                f"Error Downloading - {date_str}"
            )

        if os.path.exists(file_name):
            return make_status(
                date,
                Status.ERROR,
                f"Error Downloading - {date_str}"
            )

        try:
            blob = bucket.blob(file_name)
            blob.upload_from_filename(file_name)

            return make_status(
                date,
                Status.SUCCESS,
                f"Downloading - {date_str}"
            )

        except Exception as e:
            return make_status(
                date,
                Status.ERROR,
                str(e)
            )
        finally:
            os.remove(f"./{file_name}")





def get_password(project_id):
    secrets_client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/COMMSEC_PASSWORD/versions/latest"
    secret = secrets_client.access_secret_version(request={"name": name})
    return secret.payload.data.decode("UTF-8")


def publish(publisher, topic_path, data):
    data_str = json.dumps(data)
    data_bytes = data_str.encode('utf-8')
    try:
        future = publisher.publish(topic_path, data=data_bytes)
        future.result()
        return True
    except Exception as e:
        logger.error(f"Unable to publish to pub/sub [{e}]")
        return False


def setup_browser(browser, user, password):
    if not login(browser, user, password):
        return False, "Failed to login"
    if not goto_download(browser):
        return False, "Failed to navigate to download page"
    return True, None


def get_bucket(bucket_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    return bucket


def get_eod_data(dates):
    statuses = []
    today = datetime.now()

    bucket = get_bucket(bucket_name)
    commsec_password = get_password(project_id)

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    holidays = get_dates_from_holiday_csv('./australian-public-holidays-combined-2021-2024.csv')

    browser = get_browser('/app', headless=True)
    setup_status, msg = setup_browser(browser, commsec_user, commsec_password)
    if not setup_status:
        close_browser(browser)
        publish(publisher, topic_path, {})
        return make_status(today, Status.ERROR, msg)
    else:
        for date in dates:
            statuses.append(process_date(
                browser,
                bucket,
                date,
                holidays
            ))
        publish(publisher, topic_path, {})
        close_browser(browser)
        return statuses


def parse_date_str(date_str):
    if date_str == 'today':
        return datetime.now()
    else:
        return datetime.strptime(date_str, file_template)


def get_date_range(from_date_str, to_date_str):
    from_date = parse_date_str(from_date_str)
    to_date = parse_date_str(to_date_str)
    date_range = pd.date_range(start=to_date, end=from_date)
    dates = date_range.tolist()
    dates.reverse()

    return dates


def get_dates_from_holiday_csv(file_path):
    df = pd.read_csv(file_path)
    date_strs = df['Date'].tolist()
    dates = [str(d) for d in date_strs]
    return dates


@app.route('/')
def home():
    logger.info('This is an info log message',
                extra={'service': 'my-service', 'method': 'GET', 'endpoint': '/api/resource'})

    return 'processing...'


@app.route('/backfill/at/<at_date_str>')
def backfill_date(at_date_str):
    dates = get_date_range(at_date_str, at_date_str)
    return get_eod_data(dates)


@app.route('/backfill/from/<from_date_str>/to/<to_date_str>')
def backfill(from_date_str, to_date_str):
    dates = get_date_range(from_date_str, to_date_str)
    return get_eod_data(dates)


if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
