# pylint: disable=abstract-method, arguments-differ, no-self-use
# pylint: disable=arguments-renamed
"""Crawl a JavaScript sites"""
import logging
import pickle
import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from sylli_crawl import crawler_base
from sylli_crawl.utils import driver_manager, errors, helpers

# xpath to the "Reject all" button on youtube consent form
REJECT_ALL_XPATH = '//ytd-button-renderer[contains(., "Reject all")]'

# youtube tags and class for channel name
CHANNEL_NAME_TAG = "yt-formatted-string"
YT_CHANNEL_CLASS_NAMES = "style-scope ytd-channel-name"

# youtube tags and class for video title
VIDEO_TITLE_ELEMENT = "h1"
VIDEO_TITLE_CLASS_NAMES = "title style-scope ytd-video-primary-info-renderer"

logger = logging.getLogger(__name__)


class KhanAcademyCralwer(crawler_base.Crawler):
    """Khan Academy Crawler."""
    def __init__(self, headless=True):
        super().__init__()
        # useful for debugging
        self.headless = headless

    def _request(self, full_url, sleep_secs=10):
        """Request a given URL.

        :param str full_url: the url to request
        :param int sleep_secs: seconds to wait for browser to load
        :returns: parse page source
        :rtype: bs4.BeautifulSoup
        """
        page_source = None
        # if there are issue with the driver (it has been seen that the
        # process fails randomly on occasion) it will raise a RuntimeError
        # as the generator will not yield. We need to catch this, to make sure
        # the program does not crash
        try:
            with driver_manager.get_driver(headless=self.headless) as driver:
                driver.get(full_url)
                time.sleep(sleep_secs)
                page_source = driver.page_source
        except RuntimeError as e:
            logger.error(e)

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

    def fetch(self, url, dry_run=False):
        """Fetch a given URL.

        :param str url: the url to fetch
        :param bool dry_run: dry run flag
        :return: metadata for url
        :rtype: dict[str: str]
        """
        metadata = {}
        self._url_parse(url)
        # construct new url, we want to make sure we get rid of the
        # modal query param; if present
        full_url = f"{self.scheme}://{self.netloc}{self.path}"
        logger.info("fetching %s", full_url)

        # we dont need to go any further
        if dry_run:
            return metadata

        raw_html = self._request(full_url)
        # occasionally the driver does not return any source code.
        # this can cause problems with parsing and crash the program
        if not raw_html:
            logger.error("Driver did not return any source code")
            helpers.write_error_urls(full_url)
            return metadata
        title = self.parse_page(raw_html)

        type_ = "V"
        # find type
        for content_type in ('(video)', '(article)', '(practice)'):
            if content_type in title:
                # get first letter of content type
                type_ = content_type[1].upper()
                break

        metadata["url"] = full_url
        metadata["title"] = title
        metadata["author"] = "Khan Academy"
        metadata["type"] = type_
        metadata["source"] = f"{self.scheme}://{self.netloc}"

        return metadata


class YoutubeCrawler(crawler_base.Crawler):
    """Youtube Crawler."""
    # how to reuse session:
    # https://stackoverflow.com/questions/49764902/how-to-reuse-a-selenium-browser-session
    # https://dev.to/hardiksondagar/reuse-sessions-using-cookies-in-python-selenium-12ca
    # https://stackoverflow.com/questions/15058462/how-to-save-and-load-cookies-using-python-selenium-webdriver
    # https://medium.com/geekculture/how-to-share-cookies-between-selenium-and-requests-in-python-d36c3c8768b
    def __init__(self, headless=True):
        super().__init__()
        self.consent_passed = False
        self.cookie_file = helpers.COOKIE_PATH / "youtube-cookie.pkl"
        self.cookie_file_exists = False
        # useful for debugging
        self.headless = headless

    def _request(self, full_url, sleep_secs=10, check_consent=False):
        """Request a given URL.

        :param str full_url: the url to request
        :param int sleep_secs: seconds to wait for browser to load
        :param bool check_constant: check consent form flag
        :returns: parse page source
        :rtype: bs4.BeautifulSoup
        """
        page_source = None
        # if there are issue with the driver (it has been seen that the
        # process fails randomly on occasion) it will raise a RuntimeError
        # as the generator will not yield. We need to catch this, to make sure
        # the program does not crash
        try:
            with driver_manager.get_driver(headless=self.headless) as driver:
                driver.get(full_url)

                # optimistically try load cookies
                self.load_cookies(driver)
                time.sleep(sleep_secs)

                # check if there is source code from driver
                # this can cause unexpected errors
                source_from_driver = driver.page_source
                if source_from_driver:

                    # we need to parse the page in here so we can check for
                    # as consent modal on the page and then reuse the driver
                    # to get past it and save the cookies
                    page_source = self.parse_page(driver.page_source)

                    if not check_consent and self.has_modal(page_source):
                        logger.warning("Page may have a consent form")
                        self.consent(driver)

                    # will only save cookies if not already saved
                    self.save_cookies(driver)

                else:
                    logger.error("unable to return source from driver")
                    raise errors.SourceError

        except RuntimeError as e:
            logger.error(e)

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

    def has_captcha(self, bs4_obj):
        """Check if the page has a CAPTCHA challenge.

        We dont know exactly how a CAPTCHA challenge will be presents
        so this function tries all known CAPTCHA based attrs (from example
        html page in tests, which is from live data seen while running in
        prod) in order to maximise the chances of spotting a CAPTCHA
        challenge.

        This may be added to/changed in future as we get more data from
        prod.

        :param bs4.beautifulSoup bs4_obj: parsed html
        :returns: true if page has CAPTCHA
        :rtype: bool
        """
        # in the example html file there is a form object which contains
        # the CAPTCHA challenge
        captcha_form = bs4_obj.find_all("form", attrs={"id": "captcha-form"})
        # this is the div that contains the actual iframe within which the
        # CAPTCHA challenge sits
        captcha_div = bs4_obj.find_all("div", attrs={"class": "g-recaptcha"})
        # the div that contains the human readable text tell you to complete it
        info_div = bs4_obj.find("div", attrs={"id": "infoDiv"})
        info_contains = "CAPTCHA" in info_div.text if info_div else False
        return captcha_form != [] or captcha_div != [] or info_contains

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
        container = bs4_obj.find(
            CHANNEL_NAME_TAG, attrs={"class": YT_CHANNEL_CLASS_NAMES}
        )
        channel_name = container.select_one("a").text
        logger.info(
            "found youtube channel name: %s",
            channel_name
        )
        return channel_name

    def _video_title(self, bs4_obj):
        """Get title of video.

        :param bs4.BeautifulSoup bs4_obj: parsed html
        :return: video title
        :rtype: bool
        """
        container = bs4_obj.find(
            VIDEO_TITLE_ELEMENT, attrs={"class": VIDEO_TITLE_CLASS_NAMES}
        )
        video_title = container.select_one("yt-formatted-string").text
        logger.info(
            "found youtube video title: %s",
            video_title
        )
        return video_title

    def parse_page(self, raw_html):
        """Parse raw HTML.

        :param bytes raw_html: html from a response
        :return: parsed html
        :rtype: bs4.BeautifulSoup
        """
        bs4_obj = BeautifulSoup(raw_html, 'lxml')
        return bs4_obj

    def fetch(self, url, dry_run=False):
        """Fetch a given URL.

        :param str url: the url to fetch
        :param bool dry_run: dry run flag
        :return: metadata for url
        :rtype: dict[str: str]
        """
        metadata = {}
        self._url_parse(url)
        logger.info("fetching %s", url)

        # we dont need to go any further
        if dry_run:
            return metadata

        try:
            parsed_html = self._request(
                url,
                check_consent=self.consent_passed
            )
        except (errors.SourceError, RuntimeError):
            helpers.write_error_urls(url)

        if parsed_html and not self.has_captcha(parsed_html):
            metadata["url"] = url
            metadata["title"] = self._video_title(parsed_html)
            metadata["author"] = self._channel_name(parsed_html)
            metadata["type"] = "V"
            metadata["source"] = f"{self.scheme}://{self.netloc}"

        return metadata


class JavascriptCrawler():
    """Generic JS Crawler."""
    def __init__(self):
        self.khan_crawler = KhanAcademyCralwer()
        self.yt_crawler = YoutubeCrawler()
        logger.info("initiated youtube and khanacademy crawlers")

    def fetch(self, url, dry_run=False):
        """Fetch a JS page.

        :param str url: the url to fetch
        :param bool dry_run: dry run flag
        :return: metadata for url
        :rtype: dict[str: str]
        """
        metadata = {}
        if "khanacademy" in url:
            metadata = self.khan_crawler.fetch(url, dry_run=dry_run)

        if "youtube" in url:
            metadata = self.yt_crawler.fetch(url, dry_run=dry_run)

        return metadata
