# pylint: disable=abstract-method, arguments-differ, no-self-use
"""Crawl a HTML site"""
from bs4 import BeautifulSoup

from sylli_crawl import crawler_base
from sylli_crawl.utils import headers


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

    def fetch(self, url):
        """Fetch a given URL.

        :param str url: the url to fetch
        :return: metadata for url
        :rtype: dict[str: str]
        """
        # each new url needs to be parsed separately
        self._url_parse(url)
        # set custom host for each url
        self.headers["Host"] = self.netloc
        resp = self._request("get", url, headers=self.headers)
        title = self.parse_page(resp.text)
        return {
            "url": url,
            "title": title,
            "author": self.netloc,
            "type": "A",
            "source": self.netloc,
        }
