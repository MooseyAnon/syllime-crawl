# pylint: disable=abstract-method, arguments-differ, no-self-use
# pylint: disable=arguments-renamed
"""Crawl a JavaScript sites"""
from contextlib import contextmanager
import logging
import logging.config
from pathlib import Path
import pickle
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, WebDriverException)

from sylli_crawl import crawler_base


# xpath to the "Reject all" button on youtube consent form
REJECT_ALL_XPATH = '//ytd-button-renderer[contains(., "Reject all")]'

# youtube tags and class for channel name
CHANNEL_NAME_TAG = "yt-formatted-string"
YT_CHANNEL_CLASS_NAMES = "style-scope ytd-channel-name"

# youtube tags and class for video title
VIDEO_TITLE_ELEMENT = "h1"
VIDEO_TITLE_CLASS_NAMES = "title style-scope ytd-video-primary-info-renderer"

# browser height and width
WIDTH = "1920"
HEIGHT = "1080"

# set the logging config file
logging.config.fileConfig("logging.ini")
logger = logging.getLogger("js-crawler")


class KhanAcademyCralwer(crawler_base.Crawler):
    """Khan Academy Crawler."""
    def __init__(self):
        super().__init__()

    def _request(self, full_url, sleep_secs=10):
        """Request a given URL.

        :param str full_url: the url to request
        :param int sleep_secs: seconds to wait for browser to load
        :returns: parse page source
        :rtype: bs4.BeautifulSoup
        """
        page_source = None
        with get_driver() as driver:
            driver.get(full_url)
            time.sleep(sleep_secs)
            page_source = driver.page_source
        return page_source

    def parse_page(self, raw_html):
        """Parse page for title.

        :param bytes raw_html: raw html from from network response
        :returns: page title
        :rtype: str
        """
        bs4_obj = BeautifulSoup(raw_html, 'lxml')
        title = bs4_obj.find('title').text
        return title

    def fetch(self, url):
        """Fetch a given URL.

        :param str url: the url to fetch
        :return: metadata for url
        :rtype: dict[str: str]
        """
        self._url_parse(url)
        # construct new url, we want to make sure we get rid of the
        # modal query param; if present
        full_url = f"{self.scheme}://{self.netloc}{self.path}"
        print(full_url)
        raw_html = self._request(full_url)
        title = self.parse_page(raw_html)

        type_ = "V"
        # find type
        for content_type in ('(video)', '(article)', '(practice)'):
            if content_type in title:
                # get first letter of content type
                type_ = content_type[1].upper()
                break

        return {
            "url": full_url,
            "title": title,
            "author": "Khan Academy",
            "type": type_,
            "source": f"{self.scheme}://{self.netloc}",
        }


class YoutubeCrawler(crawler_base.Crawler):
    """Youtube Crawler."""
    # how to reuse session:
    # https://stackoverflow.com/questions/49764902/how-to-reuse-a-selenium-browser-session
    # https://dev.to/hardiksondagar/reuse-sessions-using-cookies-in-python-selenium-12ca
    # https://stackoverflow.com/questions/15058462/how-to-save-and-load-cookies-using-python-selenium-webdriver
    # https://medium.com/geekculture/how-to-share-cookies-between-selenium-and-requests-in-python-d36c3c8768b
    def __init__(self):
        super().__init__()
        self.consent_passed = False
        self.cookie_file = Path("cookies.pkl")
        self.cookie_file_exists = False

    def _request(self, full_url, sleep_secs=10, check_consent=False):
        """Request a given URL.

        :param str full_url: the url to request
        :param int sleep_secs: seconds to wait for browser to load
        :param bool check_constant: check consent form flag
        :returns: parse page source
        :rtype: bs4.BeautifulSoup
        """
        page_source = None
        with get_driver() as driver:
            driver.get(full_url)
            # optimistically try load cookies
            self.load_cookies(driver)
            time.sleep(sleep_secs)
            page_source = self.parse_page(driver.page_source)
            if not check_consent and self.has_modal(page_source):
                self.consent(driver)

            # will only save cookies if not already saved
            self.save_cookies(driver)

        return page_source

    def save_cookies(self, driver):
        """Pickle and save browser cookies.

        :param selenium.webdriver driver: the browser driver
        """
        if not self.cookie_file.exists():
            with open(self.cookie_file, "wb") as fd:
                pickle.dump(driver.get_cookies(), fd)
            logger.info("loaded saved cookies")

    def load_cookies(self, driver):
        """Load saved cookies.

        :param selenium.webdriver driver: the browser driver
        """
        logger.info("loading cookies...")
        if self.cookie_file.exists():
            with open(self.cookie_file, "rb") as fd:
                content = pickle.load(fd)
                for cookie in content:
                    driver.add_cookie(cookie)
            # test if this is needed
            driver.refresh()
            logger.info("refreshed browser")

    def consent(self, driver):
        """Navigate youtube consent form.

        :param selenium.webdriver driver: the browser driver
        """
        try:
            button = driver.find_element(By.XPATH, REJECT_ALL_XPATH)
            if button:
                logger.info("found 'Reject All' button")
                button.click()
            self.consent_passed = True

        except NoSuchElementException as e:
            logger.error("Could not find 'Reject All' button: %s", e)

    def has_modal(self, bs4_obj):
        """Check if page has modal.

        This is usually indicative of a consent form.

        :param bs4.BeautifulSoup bs4_obj: parsed html
        :return: true if modal found
        :rtype: bool
        """
        modal = bs4_obj.find_all("tp-yt-paper-dialog", attrs={"id": "dialog"})
        return modal != []

    def _channel_name(self, bs4_obj):
        """Get youtube channel name.

        :param bs4.BeautifulSoup bs4_obj: parsed html
        :returns: the channel name
        :rtype: str
        """
        channel_name = bs4_obj.find(
            CHANNEL_NAME_TAG, attrs={"class": YT_CHANNEL_CLASS_NAMES}
        )
        return channel_name.select_one("a").text

    def _video_title(self, bs4_obj):
        """Get title of video.

        :param bs4.BeautifulSoup bs4_obj: parsed html
        :return: video title
        :rtype: bool
        """
        container = bs4_obj.find(
            VIDEO_TITLE_ELEMENT, attrs={"class": VIDEO_TITLE_CLASS_NAMES}
        )
        return container.select_one("yt-formatted-string").text

    def parse_page(self, raw_html):
        """Parse raw HTML.

        :param bytes raw_html: html from a response
        :return: parsed html
        :rtype: bs4.BeautifulSoup
        """
        bs4_obj = BeautifulSoup(raw_html, 'lxml')
        return bs4_obj

    def fetch(self, url):
        """Fetch a given URL.

        :param str url: the url to fetch
        :return: metadata for url
        :rtype: dict[str: str]
        """
        self._url_parse(url)
        raw_html = self._request(url, check_consent=self.consent_passed)
        parsed_html = raw_html
        # parsed_html = self.parse_page(raw_html)
        return {
            "url": url,
            "title": self._video_title(parsed_html),
            "author": self._channel_name(parsed_html),
            "type": "V",
            "source": f"{self.scheme}://{self.netloc}",
        }


class JavascriptCrawler():
    """Generic JS Crawler."""
    def __init__(self):
        self.khan_crawler = KhanAcademyCralwer()
        self.yt_crawler = YoutubeCrawler()

    def fetch(self, url):
        """Fetch a JS page.

        :param str url: the url to fetch
        :return: metadata for url
        :rtype: dict[str: str]
        """
        metadata = {}
        if "khanacademy" in url:
            metadata = self.khan_crawler.fetch(url)

        if "youtube" in url:
            metadata = self.yt_crawler.fetch(url)

        return metadata


# https://stackoverflow.com/questions/15645093/setting-request-headers-in-selenium
# https://stackoverflow.com/questions/15397483/how-do-i-set-browser-width-and-height-in-selenium-webdriver
@contextmanager
def get_driver():
    """Configure selenium drive.

    :yields: a selenium webdriver
    :raises WebDriverException: when webdriver cannot be initialised
    """
    options = webdriver.FirefoxOptions()
    # set browser headless
    options.headless = True
    # add width and height
    options.add_argument(f"--width={WIDTH}")
    options.add_argument(f"--height={HEIGHT}")
    # set log level, we want to minimise noise
    options.add_argument("--log-level=3")
    try:
        driver = init_driver(
            options=options,
            executable_path="sylli_crawl/phantomjs/geckodriver",
        )
        yield driver

    except WebDriverException as e:
        logger.error("webdriver exception: %s", e)

    finally:
        logger.info("closing driver")
        driver.close()
        driver.quit()


def init_driver(*args, **kwargs):
    """Initialise Firefox web driver.

    :param tuple args: list of arguments to pass to driver
    :param dict kwargs: keyword arguments to pass to driver
    :returns: a Firefox web browser driver
    :rtype: selenium.webdriver
    """
    driver = webdriver.Firefox(*args, **kwargs)
    return driver
