# pylint: disable = unspecified-encoding
"""Project wide error handling."""
from datetime import datetime
import logging
import logging.config
from pathlib import Path

import requests

from . import headers

DATETIME_FORMAT = "%d-%m-%Y-%H:%M:%S"
ERROR_DIR = Path("files/html-error-dumps")
TEST_FILE_DIR = Path("tests")


class ConsentParseError(ValueError):
    """Could not find correct values to navigate consent form."""


class ParseError(ValueError):
    """Could not find any of the CSS classes/IDs or HTML tags."""


# set the logging config file
logging.config.fileConfig("logging.ini")
logger = logging.getLogger(__name__)


def get(url):
    """Get a URL.

    :param str url: the url to fetch
    :returns: a response object
    :rtype: requests.Response
    """
    resp = requests.get(
        url, headers=headers.firefox_headers(), timeout=1)
    return resp


def dump_html(bs4_obj, crawler_name):
    """Dump HTML to a file.

    This is mainly for debugging purposes.

    :param bs4.BeautifulSoup bs4_obj: parsed HTML page
    :param str crawler_name: name of crawler to prepend to file name
    """
    now = datetime.now()
    formatted_dt = now.strftime(DATETIME_FORMAT)
    full_path = ERROR_DIR / f"{crawler_name}-{formatted_dt}.html"
    # dump to file
    with open(full_path, "w") as fd:
        fd.write(str(bs4_obj.prettify()))


def save_test_html(url, tests_file_path):
    """Save test HTML.

    This is for creating new test cases.

    :param str url: url of test case page
    :param str tests_file_path: the director to save file to (HTML | PDF)
    :raises requests.HTTPError: when unable to make request
    """
    resp = get(url)
    if not resp.ok:
        raise requests.HTTPError(
            "There was a problem requesting test url.\n"
            f"url: {url}\n"
            f"Status code: {resp.statu_code}"
        )
    full_path = TEST_FILE_DIR / tests_file_path
    with open(full_path, "w") as fd:
        fd.write(resp.text)

    logger.info("saved file to %s", full_path)
