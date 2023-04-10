# pylint: disable=abstract-method, arguments-differ, no-self-use
"""Crawl a HTML site"""
import logging

from bs4 import BeautifulSoup
import requests

from sylli_crawl import crawler_base
from sylli_crawl.utils import headers, helpers

logger = logging.getLogger(__name__)


class HTMLCrawler(crawler_base.Crawler):
    """HTML Crawler."""
    def __init__(self):
        # init parent class to get access to class properties
        super().__init__()
        self.headers = headers.firefox_headers()

    def parse_page(self, raw_html):
        """Parse the page HTML.

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
        resp = None
        # each new url needs to be parsed separately
        self._url_parse(url)
        # set custom host for each url
        self.headers["Host"] = self.netloc

        logger.info("fetching: %s", url)

        # we dont need to go any further
        if dry_run:
            return metadata

        try:
            resp = self._request("get", url, headers=self.headers)

        except requests.exceptions.RequestException as e:
            logger.error(e)
            helpers.write_error_urls(url)

        if resp:
            # temp solution till refactor
            try:
                title = self.parse_page(resp.text)
                # add metadata
                metadata["url"] = url
                metadata["title"] = title
                metadata["author"] = self.netloc
                metadata["type"] = "A"
                metadata["source"] = self.netloc
            # we've received a weird page that we cant parse or something
            # on the page has changed
            except AttributeError as e:
                logger.error(e)
                # double check we actually have any source code
                if resp:
                    helpers.dump_pretty_html(
                        BeautifulSoup(resp.text, 'lxml'), "html")

        return metadata
