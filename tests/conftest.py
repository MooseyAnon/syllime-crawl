
import datetime

import pytest
import requests


TESTS_DIR = "tests/html-files"


@pytest.fixture(name="mock_request")
def _mock_request():
    print("in mock request")
    def ret_html(file_path):
        print("in ret_")
        full_file_path = f"{TESTS_DIR}/{file_path}"
        html_str = None
        with open(full_file_path, "r") as rf:
            html_str = rf.read()
        return html_str
    return ret_html


@pytest.fixture(name="response_object")
def _response_object():
    # docs: https://requests.readthedocs.io/en/latest/_modules/requests/models/#Response
    def set_status(text=None, status_code=200, url="https://some-fake.site"):
        resp = requests.Response()
        resp._content = bytes(text,'UTF-8')
        resp.status_code = status_code
        resp.url = url
        return resp
    return set_status


@pytest.fixture(name="response")
def _response(mock_request, response_object):
    def inner(file_path, status_code=200):
        text = mock_request(file_path)
        resp = response_object(text=text, status_code=status_code)
        return resp
    return inner


@pytest.fixture(name="fake_datetime")
def _fake_datetime():
    # returns 01/01/2023-01:00:00
    return datetime.datetime(year=2023, month=1, day=1, hour=1)
