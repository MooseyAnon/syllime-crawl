# pylint: disable=arguments-differ, no-self-use, consider-using-f-string
"""Crawler for Google search engine."""
import logging
import logging.config
import re
import time

from bs4 import BeautifulSoup

from sylli_crawl import crawler_base
from sylli_crawl.utils import errors, headers

# variable name to look for in script tag in consent modal
CONSENT_VAR_NAME = "rAU"
# currently working css class to search for
LAST_WORKING_CSS_CLASS = "yuRUbf"

# we should keep a list of previously seen class
# attrs, so we can search as backups
# NOTE: currently working class should at start of this list
# NOTE 2: css classes google uses seem to be dependant on location
# and js status
PREVIOUSLY_SEEN_CSS_CLASSES = [LAST_WORKING_CSS_CLASS, "g", "kCrYT"]

# the html element to search for
HTML_ELEMENT = "div"

# tag for video area on SREP
VIDEO_ELEMENT_TAG = "video-voyager"

# set the logging config file
logging.config.fileConfig("logging.ini")
logger = logging.getLogger("google-crawler")


class GoogleCrawler(crawler_base.Crawler):
    """Google crawler object."""
    def __init__(self):
        super().__init__("https://www.google.com/search")
        self.headers = self.set_headers()
        self.parsed_html = None
        self.consent_url = "https://consent.google.com/save"

    def set_headers(self):
        """Set headers for crawler."""
        h = headers.firefox_headers()
        h["Sec-Fetch-Site"] = "same-origin"
        return h

    def _clean_url(self, url):
        """Clean Google SERP links.

        Links from Google's SERP can be messy or badly formatted
        in various was, this function cleans the urls so only the
        relevant part is saved.

        :param str url: the url to clean
        :returns: a cleaned url
        :rtype: str
        """
        out = []
        char = 0
        # some of googles search results start with /url?=
        while url[char] != "h":
            char += 1
        # add url to out until we see an & because we dont care
        # about extra query params, we just want the full
        # clean url
        while char < len(url):
            if url[char] == "&":
                break

            out.append(url[char])
            char += 1

        return "".join(out)

    def _build_consent_url(self, s):
        """Construct url for consent form.

        :param str s: a string containing google consent tokens
        :returns: a correctly formatted consent url
        :rtype: str
        """
        tokens = {
            "continue": None,
            "gl": "GB",
            "m": "0",
            "pc": "srp",
            "x": "5",
            "src": "2",
            "hl": "en",
            "bl": None,
            "uxe": "none",
            "set_eom": "true",
        }

        out = []
        for k, v in tokens.items():
            if v:
                out.append(f"{k}={v}")
                continue

            pat = f"{k}=([^&]+)"
            match = re.search(pat, s)
            if match:
                out.append(match.group())

        return "&".join(out)

    def construct_query(self, query, page=1):
        """Construct a Google search engine query.

        :param str query: space separated query
        :param int page: the page number to request
        :raises ValueError: when page number invalid
        :returns: a fully formed Google query url
        :rtype: str
        """
        # may be useful for future query formatting:
        # https://moz.com/blog/
        # the-ultimate-guide-to-the-google-search-parameters
        if page < 1:
            raise ValueError("Pages must be 1 or higher")
        full_url = "{}://{}{}?q={}&start={}&safe=strict&ie=UTF-8".format(
            self.scheme,
            self.netloc,
            self.path,
            "+".join(query.split(" ")),
            (page - 1) * 10,
        )
        return full_url

    def _consent(self, parsed_html):
        """Navigate Google consent modal.

        :param bs4.BeautifulSoup parsed_html: parsed_html
        :raises errors.ConsentParseError: when failure during
            consent navigation occurs
        """

        # find url string
        pattern = f"{CONSENT_VAR_NAME}=([^;]+)"
        script = parsed_html.find_all("script")
        s = None
        for i in script:
            f = re.search(pattern, i.string)
            if f:
                s = f.group()[5:-1]
                break

        if not s:
            raise errors.ConsentParseError(
                f"no match found for {CONSENT_VAR_NAME}")

        # clean string and remove badly encoded chars
        out = []
        char = 0
        while char < len(s):
            if s[char] == "\\":
                t = ''
                i = 0
                while i < 4:
                    t += s[char]
                    char += 1
                    i += 1
                # replace hex encoded chars with unicode
                if t == r"\x3d":
                    out.append("=")
                elif t == r"\x26":
                    out.append("&")
                else:
                    logger.warning(
                        "unrecognised encoded character: %s", t)

            out.append(s[char])

            char += 1

        m = "".join(out)
        url = f"{self.consent_url}?{self._build_consent_url(m)}"
        # send post request to pass consent page
        logger.info("consent url: %s", url)
        resp = self._request("post", url, data=None, headers=self.headers)
        # this is a no content request so should return 204
        if not resp or resp.status_code not in range(200, 211):
            raise errors.ConsentParseError("Failed to pass consent")

    def _create_bs4_obj(self, raw_html):
        """Create bs4 object and bind to class property.

        :param bytes raw_html: html from response object
        :return: parsed html
        :rtype: bs4.BeautifulSoup
        """
        self.parsed_html = BeautifulSoup(raw_html, 'lxml')
        return self.parsed_html

    def has_modal(self, bs4_obj):
        """Check if page has modal.

        This is usually indicative of a consent form.
        :param bs4.BeautifulSoup bs4_obj: parsed_html
        :return: true is there is a modal else false
        :rtype: bool
        """
        modal = bs4_obj.find_all("div", attrs={"aria-modal": "true"})
        return modal != []

    def parse_video(self, bs4_obj):
        """Get any video links on the Page.

        :param bs4.BeautifulSoup bs4_obj: parsed html page
        :returns: a list of video links
        :rtype: list[str]
        """
        out = []
        for video in bs4_obj.find_all(VIDEO_ELEMENT_TAG):
            anchor = video.select_one("a[href]")
            if anchor:
                out.append(anchor["href"])
        return out

    def parse_page(self, bs4_obj):
        """Parse a Google SERP.

        :param bs4.BeautifulSoup bs4_obj: parsed html
        :returns: array of links from Google SERP
        :rtype: list[str]
        :raises errors.ParseError: when no css classes are matched
        """
        if self.has_modal(bs4_obj):
            wait_time = 5
            logger.warning(
                "Page has consent modal. Waiting %ss before making request",
                wait_time
            )
            time.sleep(wait_time)
            self._consent(bs4_obj)

        search_res = None
        for css_class in PREVIOUSLY_SEEN_CSS_CLASSES:
            search_res = bs4_obj.find_all(
                f"{HTML_ELEMENT}", attrs={"class": f"{css_class}"})
            if search_res:
                logger.info("Found matching CSS class: %s", css_class)
                break

        if not search_res:
            raise errors.ParseError(
                "None of the previously matched css "
                "classes have been found.")

        out_arr = []
        for res in search_res:
            anchor = res.select_one("a")
            if anchor is not None:
                out_arr.append(self._clean_url(anchor["href"]))
        # add any videos found to the current output
        out_arr += self.parse_video(bs4_obj)
        return out_arr

    def fetch(self, query, page=1):
        """Fetch a query.

        :param str query: the query to search for
        :param int page: the results page of the query
        :return: an array of links from Bings SERP
        :rtype: list[str]
        """
        # construct url
        full_url = self.construct_query(query, page)
        logger.info("calling: %s", full_url)
        # make request
        resp = self._request("get", full_url, headers=self.headers)
        if self.consent_url in resp.url:
            logger.warning("redirected to consent page.")
        # parse page
        out_arr = None
        try:
            bs4_obj = self._create_bs4_obj(resp.text)
            out_arr = self.parse_page(bs4_obj)

        except (errors.ConsentParseError, errors.ParseError) as err:
            logger.error("could not parse page, dumping HTML: %s", err)
            errors.dump_html(self.parsed_html, "google")

        return out_arr
