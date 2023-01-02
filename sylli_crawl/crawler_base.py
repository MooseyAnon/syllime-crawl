"""Base module for crawlers."""
from urllib.parse import urlparse

import requests


class Crawler:
    """Base class for all crawlers."""
    def __init__(self, full_url=None):
        """Crawler init

        :param str full_url: a url this crawler will function on
        """
        self.full_url = full_url

        # parsed url -->
        self.scheme = None
        self.netloc = None
        self.path = None
        self.params = None
        self.query = None
        self.fragment = None

        # website metadata -->
        self.is_js = None
        self.is_pdf = None
        self.is_html = None

        # header information -->
        self.headers = None

        # parse url -->
        if self.full_url:
            self._url_parse(self.full_url)

        # session
        self.session = requests.Session()

    def _url_parse(self, url):
        """Thin wrapper around urlparse

        :param str url: the url to parse
        """
        parsed_url = urlparse(url)
        # assign to attrs
        self.scheme = parsed_url.scheme
        self.netloc = parsed_url.netloc
        self.path = parsed_url.path
        self.params = parsed_url.params
        self.query = parsed_url.query
        self.fragment = parsed_url.fragment

    # pylint: disable=unused-argument
    def _request(self, method, full_url, timeout=1, **kwargs):
        """Think wrapper around a requests session.

        This will be used for the duration of the program by each
        crawler.

        :param str method: http method (normal CRUD)
        :param str full_url: the full url to request
        :param int timeout: length of time before requests time out
        :param dict kwargs: other optional params for request.session
        :return: a response object
        :rtype: request.Response
        """
        resp = self.session.request(
            method,
            full_url,
            timeout=5,
            **kwargs,
        )
        resp.raise_for_status()
        return resp

    def set_headers(self):
        """Set request headers."""
        raise NotImplementedError

    def fetch(self, *kwargs):
        """Fetch a url.

        This is the standard interface that will be used across
        all crawler types, however each will have to deal with its
        own implementation details.

        :param dict kwargs: url and optional params needed to fetch data
        """
        raise NotImplementedError
