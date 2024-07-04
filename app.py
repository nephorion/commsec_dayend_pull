import os
from enum import Enum
import logging
import json
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from google.cloud import storage
from google.cloud import secretmanager
from google.cloud import pubsub_v1
from flask import Flask, jsonify
from datetime import datetime, timedelta
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
    file_list = []
    for blob in blobs:
        file_list.append(blob.name)
    return file_list


def make_file_name(date):
    return f"ASXEQUITIESStockEasy-{date.strftime(file_template)}.txt"


def file_exists(bucket, date):
    blob = bucket.blob(make_file_name(date))
    return blob.exists()


Status = Enum('Status', 'SUCCESS ERROR SKIPPED_WEEKEND SKIPPED_HOLIDAY SKIPPED_EXISTS')
def make_status(date, status:Status, msg):
    return {
        'date': date.strftime(file_template),
        'status': status.name,
        'code': status.value,
        'msg': msg
    }

def process_date(browser, bucket, date):
    if not file_exists(bucket, date):
        if date.weekday() < 5:
            if download(browser, date):
                file_name = make_file_name(date)

                if os.path.exists(file_name):
                    try:
                        blob = bucket.blob(file_name)
                        blob.upload_from_filename(file_name)

                        return make_status(
                            date,
                            Status.SUCCESS,
                            f"Downloading - {date.strftime(file_template)}"
                        )

                    except Exception as e:
                        return make_status(
                            date,
                            Status.ERROR,
                            str(e)
                        )
                    finally:
                        os.remove(f"./{file_name}")
                else:
                    return make_status(
                        date,
                        Status.ERROR,
                        f"Error Downloading - {date.strftime(file_template)}"
                    )


            else:
                return make_status(
                    date,
                    Status.ERROR,
                    f"Error Downloading - {date.strftime(file_template)}"
                )

        else:
            return make_status(
                date,
                Status.SKIPPED_WEEKEND,
                f"Skipped Downloading(Weekend) - {date.strftime(file_template)}"
            )
    else:
        return make_status(
            date,
            Status.SKIPPED_EXISTS,
            f"Skipped Downloading(Exists) - {date.strftime(file_template)}"
        )


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
    except:
        return False


@app.route('/')
def home():
    logger.info('This is an info log message',
                extra={'service': 'my-service', 'method': 'GET', 'endpoint': '/api/resource'})

    return 'processing...'


def get_eod_data(date):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    current_date = date

    commsec_password = get_password(project_id)

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    browser = get_browser('/app', headless=True)
    if not login(browser, commsec_user, commsec_password):
        return jsonify(make_status(
            date,
            Status.ERROR,
            "Failed to login"
        ))
    if not goto_download(browser):
        return jsonify(make_status(
            date,
            Status.ERROR,
            "Failed to navigate to download page"
        ))


    status = process_date(
        browser,
        bucket,
        current_date
    )

    close_browser(browser)

    return status


@app.route('/today')
def today():
    return get_eod_data(datetime.now())

@app.route('/backfill/<date_str>')
def backfill_date(date_str):
    return get_eod_data(datetime.strptime(date_str, file_template))

@app.route('/backfill')
def backfill():
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    current_date = datetime.now()
    end_date = datetime.fromisoformat('2021-07-03')

    commsec_password = get_password(project_id)

    browser = get_browser('/app', headless=True)

    if not login(browser, commsec_user, commsec_password):
        return jsonify(make_status(
            current_date,
            Status.ERROR,
            "Failed to login"
        ))
    if not goto_download(browser):
        return jsonify(make_status(
            current_date,
            Status.ERROR,
            "Failed to navigate to download page"
        ))

    finished = False
    statuses = []
    while not finished:
        if current_date <= end_date:
            finished = True
        else:
            statuses.append(
                process_date(
                    browser,
                    bucket,
                    current_date
                )
            )
        current_date = current_date - timedelta(days=1)

    close_browser(browser)

    return statuses


if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
