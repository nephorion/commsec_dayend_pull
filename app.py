import os
import time
from google.cloud import storage
from google.cloud import secretmanager
from flask import Flask
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

bucket_name = os.getenv('BUCKET')
commsec_user = os.getenv('COMMSEC_USER')
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

# pylint: disable=C0103
app = Flask(__name__)

file_template = '%Y%m%d'
query_template = '%d%m%Y'


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

def make_status(date, status):
    return {
        'date': date.strftime(file_template),
        'status': status
    }

def process_date(browser, bucket, date):
    if not file_exists(bucket, date):
        if date.weekday() < 5:
            return(f"Downloading - {date.strftime(file_template)}")
            download(browser, date)
        else:
            #pass
            return("Skipped Weekend")
    else:
        #pass
        return("Skipped Already Exists")


def get_password(project_id):
    secrets_client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/COMMSEC_PASSWORD/versions/latest"
    secret = secrets_client.access_secret_version(request={"name": name})
    return secret.payload.data.decode("UTF-8")


def login(username, password, destination):
    login_url = 'https://www2.commsec.com.au/secure/login'
    data_url = 'https://www2.commsec.com.au/Private/Charts/EndOfDayPrices.aspx'

    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory":destination}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    browser = webdriver.Chrome(options=options)
    browser.get(login_url)
    username_input = browser.find_element(By.ID, "username")
    username_input.send_keys(username)
    password_input = browser.find_element(By.ID, "password")
    password_input.send_keys(password)

    login_btn = browser.find_element(By.ID, "login")
    login_btn.click()
    time.sleep(2)

    browser.get(data_url)
    time.sleep(2)
    return browser

def download(browser, date):
    type_select = Select(browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_ddlAllSecurityType_field"))
    type_select.select_by_visible_text("ASX Equities")
    format_select = Select(browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_ddlAllFormat_field"))
    format_select.select_by_visible_text("Stock Easy")
    date_input = browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_txtAllDate_field")
    date_input.clear()
    date_input.send_keys(date.strftime(query_template))
    download_btn = browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_btnAllDownload_implementation_field")
    download_btn.click()
    time.sleep(.5)

@app.route('/today')
def get_eod_data():
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    current_date = datetime.now()

    commsec_password = get_password(project_id)

    browser = login(commsec_user, commsec_password, '/app')

    status = process_date(
        browser,
        bucket,
        current_date
    )
    browser.quit()

    return [make_status(current_date,status+" "+commsec_user+" "+commsec_password)]


@app.route('/backfill')
def get_backfill_data():
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    current_date = datetime.now()
    end_date = datetime.fromisoformat('2021-07-03')

    commsec_password = get_password(project_id)

    browser = login(commsec_user, commsec_password, '/app')

    finished = False
    statuses = []
    while not finished:
        if current_date <= end_date:
            finished = True
        else:
            statuses.append(
                make_status(
                    current_date,
                    process_date(
                        browser,
                        bucket,
                        current_date
                    )
                )
            )
        current_date = current_date - timedelta(days=1)

    browser.quit()

    return statuses


if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
