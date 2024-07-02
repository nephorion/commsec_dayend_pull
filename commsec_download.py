import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_browser(destination, headless=True):
    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": destination}
    options.add_experimental_option("prefs", prefs)
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(options=options)
    return browser


def login(browser, username, password):
    login_url = 'https://www2.commsec.com.au/secure/login'
    browser.get(login_url)

    username_input = browser.find_element(By.ID, "username")
    username_input.send_keys(username)
    password_input = browser.find_element(By.ID, "password")
    password_input.send_keys(password)

    login_btn = browser.find_element(By.ID, "login")
    login_btn.click()

    wait = WebDriverWait(browser, timeout=10)
    try:
        home = wait.until(EC.presence_of_element_located((By.ID, "home")))
        if home is not None:
            return True
        else:
            return False
    except:
        return False



def goto_download(browser):
    data_url = 'https://www2.commsec.com.au/Private/Charts/EndOfDayPrices.aspx'
    browser.get(data_url)

    wait = WebDriverWait(browser, timeout=10)
    dl = wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_ddlAllSecurityType_field")))

    try:
        if dl is not None:
            return True
        else:
            return False
    except:
        return False


def download(browser, date):
    query_template = '%d%m%Y'

    try:
        type_select = Select(
            browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_ddlAllSecurityType_field"))
        type_select.select_by_visible_text("ASX Equities")
        format_select = Select(browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_ddlAllFormat_field"))
        format_select.select_by_visible_text("Stock Easy")
        date_input = browser.find_element(By.ID, "ctl00_BodyPlaceHolder_EndOfDayPricesView1_txtAllDate_field")
        date_input.clear()
        date_input.send_keys(date.strftime(query_template))
        download_btn = browser.find_element(By.ID,
                                            "ctl00_BodyPlaceHolder_EndOfDayPricesView1_btnAllDownload_implementation_field")
        download_btn.click()
        time.sleep(.5)
        return True
    except:
        return False

def close_browser(browser):
    time.sleep(3)
    browser.quit()


if __name__ == '__main__':
    import os
    from datetime import datetime
    from dotenv import load_dotenv
    load_dotenv()
    commsec_user = os.getenv('COMMSEC_USER')
    commsec_password = os.getenv('COMMSEC_PASSWORD')

    test_browser = get_browser('', headless=False)
    if login(test_browser, commsec_user, commsec_password):
        print("Login Success")
        goto_download(test_browser)
        download(test_browser, datetime.now())
    else:
        print("Login Error")

    close_browser(test_browser)