# pylint: disable = unspecified-encoding
"""Shared helpers."""

from datetime import datetime
import json
import logging
import os
import pathlib
import pickle
import random
import time

import requests

from . import headers
from .driver_manager import get_driver

logger = logging.getLogger(__name__)

# set file globals
COOKIE_PATH = pathlib.Path(os.environ.get("COOKIE_PATH", "cookies"))
ERROR_DIR = pathlib.Path(os.environ.get("ERROR_DIR", "files/html-error-dumps"))
ERROR_URL_FILE = pathlib.Path(
    os.environ.get("ERROR_URL_FILE", "files/error-urls.json"))
TEST_FILE_DIR = pathlib.Path(os.environ.get("TEST_FILE_DIR", "tests"))


def wait(start=6, end=45):
    """Wait for a random time period chosen from a range.

    :param int start: start of the range
    :param int end: end of the range
    """
    sleep_time = random.choice(range(start, end + 1))
    logger.info("sleeping for %s", sleep_time)
    time.sleep(sleep_time)


def get(url):
    """Get a URL.

    :param str url: the url to fetch
    :returns: a response object
    :rtype: requests.Response
    """
    resp = requests.get(
        url, headers=headers.firefox_headers(), timeout=1)
    return resp


def mkdir(path):
    """Recursively make directories in a path.

    Note: this is only here to make logging a bit cleaner.

    :param pathlib.Path path: path or directory to make
    """
    if not isinstance(path, pathlib.Path):
        logger.warning(
            "path must a pathlib.Path object, attempting to convert"
        )
        path = pathlib.Path(path)

    # recursively make path
    path.mkdir(parents=True, exist_ok=True)


def write_html(data, file_path):
    """Write HTML to a file.

    :param str data: the data to be written
    :param pathlib.Path file_path: location to write to
    """
    with open(file_path, "w") as fd:
        fd.write(data)
    logger.info("saved file to %s", file_path)


def read_json(path):
    """Read a JSON file.

    :param pathlib.Path path: the full path to the JSON file
    :returns: contents of the json file
    :rtype: dict
    :raises ValueError: if file does not exist
    :raises json.JSONDecodeError: if file cannot be parsed
    """
    contents = None  # will be returned regardless of any errors
    if not path.exists():
        logger.error("%s does not exist", path)
        return contents

    with open(path, "r") as fd:
        try:
            contents = json.load(fd)
        except json.JSONDecodeError as e:
            logger.error(e)
    return contents


def write_json(data, path):
    """Save data as JSON.

    :param dict data: data to be saved
    :param pathlib.Path path: location to save data
    """
    with open(path, "w") as fd:
        json.dump(data, fd, indent=4)


def dump_pretty_html(bs4_obj, crawler_name):
    """Dump HTML to a file.

    This is mainly for debugging purposes.

    :param bs4.BeautifulSoup bs4_obj: parsed HTML page
    :param str crawler_name: name of crawler to prepend to file name
    """
    now = datetime.now()
    formatted_dt = now.strftime("%d-%m-%Y-%H:%M:%S")
    full_path = ERROR_DIR / f"{crawler_name}-{formatted_dt}.html"
    # dump to file
    write_html(str(bs4_obj.prettify()), full_path)


def save_test_html(url, tests_file_path):
    """Save test HTML.

    This is for creating new test cases.

    :param str url: url of test case page
    :param str tests_file_path: the directory to save file to (HTML | PDF)
    :raises requests.HTTPError: when unable to make request
    """
    resp = get(url)
    if not resp.ok:
        raise requests.HTTPError(
            "There was a problem requesting test url.\n"
            f"url: {url}\n"
            f"Status code: {resp.status_code}"
        )
    full_path = TEST_FILE_DIR / tests_file_path
    write_html(resp.text, full_path)


def save_cookies(save_file, url):
    """Pickle generic browser cookies.

    This uses selenium to get the browser cookies.

    :param str save_file: path to write to
    :param str url: the url to request
    """
    with get_driver(headless=True) as driver:
        driver.get(url)
        wait(start=10, end=15)
        with open(save_file, "wb") as fd:
            pickle.dump(driver.get_cookies(), fd)

    logging.info("browser cookies successfully saved.")


def write_error_urls(url):
    """Record URLs that result in a HTTP error.

    This is to allow for further investigation. Many times
    cloudflare websites return a 5xx response when the challenge
    has failed so it is useful to record these URL to check if it
    is a cloudflare issue or not.

    :param str url: the url that raised the HTTPError
    """

    logger.info("saving %s to url error file", url)
    # optimistic read
    pre_existing_errors = read_json(ERROR_URL_FILE)
    if not pre_existing_errors:
        pre_existing_errors = {"errors": []}

    pre_existing_errors["errors"].append(url)
    write_json(pre_existing_errors, ERROR_URL_FILE)
