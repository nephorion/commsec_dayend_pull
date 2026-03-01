import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from CustomException import CustomException


def get_browser(destination, headless=True):
    """
    Method to get a Chrome browser instance.

    :param destination: Path to the download directory.
    :type destination: str

    :param headless: Flag to run the browser in headless mode. Default is True.
    :type headless: bool

    :return: Chrome browser instance.
    :rtype: selenium.webdriver.chrome.webdriver.WebDriver
    """
    try:
        options = webdriver.ChromeOptions()
        prefs = {"download.default_directory": destination}
        options.add_experimental_option("prefs", prefs)
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        browser = webdriver.Chrome(options=options)
        return browser
    except Exception as e:
        raise CustomException(e, f"Failed to get browser")


def login(browser, username, password):
    """
    Login to a given website using a web browser.

    :param browser: The web browser instance to use.
    :param username: The username to login with.
    :param password: The password to login with.
    :return: None
    """
    login_url = 'https://www2.commsec.com.au/secure/login'
    try:
        browser.get(login_url)

        username_input = browser.find_element(By.ID, "username")
        username_input.send_keys(username)
        password_input = browser.find_element(By.ID, "password")
        password_input.send_keys(password)

        login_btn = browser.find_element(By.ID, "login")
        login_btn.click()

        wait = WebDriverWait(browser, timeout=10)
        home = wait.until(EC.presence_of_element_located((By.ID, "home")))
    except Exception as e:
        raise CustomException(e, f"Failed to login [{login_url}] [{username}]")


def goto_download(browser):
    """
    Navigates the given browser to the download page.

    :param browser: The browser object used for navigation.
    :return: None
    """
    data_url = 'https://www2.commsec.com.au/Private/Charts/EndOfDayPrices.aspx'
    try:
        browser.get(data_url)

        wait = WebDriverWait(browser, timeout=10)
        dl = wait.until(
            EC.presence_of_element_located((
                By.ID,
                "ctl00_BodyPlaceHolder_EndOfDayPricesView1_ddlAllSecurityType_field"
            ))
        )
    except Exception as e:
        raise CustomException(e, f"Failed to navigate to download page [{data_url}]")


def download(browser, date):
    """
    Method to download data from a browser.

    :param browser: The browser object to use for downloading.
    :param date: The date for which the data should be downloaded.
    :type date: datetime.datetime
    :return: None
    """
    try:
        query_template = '%d%m%Y'

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

    except Exception as e:
        raise CustomException(e, f"Failed to download [{date}]")


def close_browser(browser):
    """
    Close the browser.

    :param browser: The browser instance to close.
    :return: None
    """
    try:
        time.sleep(3)
        browser.quit()
    except Exception as e:
        raise CustomException(e, f"Failed to close browser")


if __name__ == '__main__':
    import os
    from datetime import datetime
    from dotenv import load_dotenv

    load_dotenv()
    commsec_user = os.getenv('COMMSEC_USER')
    commsec_password = os.getenv('COMMSEC_PASSWORD')

    test_browser = get_browser('', headless=False)
    try:
        login(test_browser, commsec_user, commsec_password)
        print("Login Success")
        goto_download(test_browser)
        download(test_browser, datetime.now())
    except Exception as ex:
        print(ex)

    close_browser(test_browser)
