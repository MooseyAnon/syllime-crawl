# pylint: disable=arguments-differ, no-self-use, consider-using-f-string
"""Crawler for Bing search engine."""
import time

from bs4 import BeautifulSoup

from sylli_crawl import crawler_base
from sylli_crawl.utils import errors, headers

# currently working css class to search for
LAST_WORKING_CSS_CLASS = "b_algo"

# this is for bings SER container element
LAST_WORKING_HTML_ID = "b_results"

# we should keep a list of previously seen class
# attrs, so we can search as backups
# NOTE: currently working class should at start of this list
PREVIOUSLY_SEEN_CSS_CLASSES = [LAST_WORKING_CSS_CLASS]

# the html elements to search for
HTML_ELEMENT = "li"

# the element that contains the search results
SER_CONTAINER_OBJ = "ol"


class BingCrawler(crawler_base.Crawler):
    """Bing crawler object."""
    def __init__(self):
        super().__init__("https://www.bing.com/search")
        self.headers = self.set_headers()
        self.parsed_html = None

    def _create_bs4_obj(self, raw_html):
        """Create bs4 object and bind to class property.

        :param bytes raw_html: html from response object
        :return: parsed html
        :rtype: bs4.BeautifulSoup
        """
        self.parsed_html = BeautifulSoup(raw_html, 'lxml')
        return self.parsed_html

    def _handle_parse_error(self, bs4_obj):
        """Handle errors parsing SERP.

        :param bs4.BeautifulSoup bs4_obj: parsed HTML page
        """
        err_container = bs4_obj.find(
            "li", attrs={"class": "b_no"})
        if err_container and err_container.find("h1"):
            err_msg = err_container.find("h1").text
            print("ERROR: ", err_msg)
        else:
            err_msg = (
                "None of the previously matched css classes have been found. "
                "Page may have changed.")
            print(errors.ParseError(err_msg))

    def parse_with_retry(
        self, full_url, retries=10, backoff=1.5, max_wait=15
    ):
        """Make try parse SERP with retries.

        There are case where bing return a 'could not find matching results'
        page for not apparent reason. This is usually resolved by retrying
        the request.

        This function wraps around the self._request function and adds retries
        with backoff functionality.

        :param str full_url: url to request
        :param int retries: the maximum number of retries
        :param float backoff: backoff multiplier
        :param int max_wait: maximum length of any single wait during backoff

        :returns: an array of bing results or None
        :rtype: list[str] | None
        """
        out_arr = None
        # backoff mechanism while we wait for a result
        attempts = 1
        next_wait_time = 1
        while next_wait_time < max_wait and attempts <= retries:
            resp = self._request("get", full_url, headers=self.headers)
            # parse page
            parsed_html = self._create_bs4_obj(resp.text)
            out_arr = self.parse_page(parsed_html)

            if out_arr:
                break

            # backoff
            print(f"Did not get any results after {attempts} attempts, "
                  f"sleeping for {next_wait_time}")
            time.sleep(next_wait_time)
            attempts += 1
            next_wait_time *= backoff

        return out_arr

    def set_headers(self):
        """Set headers for crawler.

        :return: headers
        :rtype: dict[str, str]
        """
        h = headers.chrome_headers()
        h["Host"] = self.netloc
        return h

    def construct_query(self, query, page=1):
        """Construct a Bing search engine query.

        :param str query: space separated query
        :param int page: the page number to request
        :raises ValueError: when page number invalid
        :returns: a fully formed Bing query url
        :rtype: str
        """
        if page < 1:
            raise ValueError("Pages must be 1 or higher")
        full_url = "{}://{}{}?q={}&first={}".format(
            self.scheme,
            self.netloc,
            self.path,
            "+".join(query.split(" ")),
            (page * 10) - 9,
        )
        return full_url

    def parse_page(self, bs4_obj):
        """Parse a Bing SERP.

        :param bs4.BeautifulSoup bs4_obj: parsed html
        :returns: array of links from Bing SERP
        :rtype: list[str]
        :raises errors.ParseError: when no css classes are matched
        """
        # all bing results are in a "results" ol element container
        ol_container = bs4_obj.find(
            f"{SER_CONTAINER_OBJ}", attrs={"id": f"{LAST_WORKING_HTML_ID}"})
        # narrow down our search for the actual SERP results
        search_res = None
        for css_class in PREVIOUSLY_SEEN_CSS_CLASSES:
            search_res = ol_container.find_all(
                f"{HTML_ELEMENT}", attrs={"class": f"{css_class}"})
            if search_res:
                print(f"Found matching css class: {css_class}")
                break

        if not search_res:
            self._handle_parse_error(bs4_obj)
            return None

        out_arr = []
        for res in search_res:
            title = res.find("div", attrs={"class": "b_title"})
            if not title:
                # only the first page has results wrapped in a div
                # with "b_title" class
                title = res.find("h2")

            # on firefox bing uses a redirect and the real url is
            # available under `hover-url`, we can search for `href` when
            # using chrome headers
            anchor = title.select_one("a[href]")
            if anchor is not None:
                out_arr.append(anchor["href"])

        # this means there was some kind of error
        if not out_arr:
            self._handle_parse_error(bs4_obj)

        return out_arr

    def fetch(self, query, page=1):
        """Fetch a query.

        :param str query: the query to search for
        :param int page: the results page of the query
        :return: an array of links from Bings SERP
        :rtype: list[str]
        """
        print("constructing url...")
        # construct url
        full_url = self.construct_query(query, page)
        print(f"constructed url: {full_url}")
        out = self.parse_with_retry(full_url)
        if not out:
            print(
                f"No search results matching the query: {query}, dumping file")
            errors.dump_html(self.parsed_html, "bing")
        return out
