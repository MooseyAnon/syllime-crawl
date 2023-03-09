import pytest

from selenium.common.exceptions import WebDriverException

from sylli_crawl import js_crawler
from sylli_crawl.utils import driver_manager


class MockDriver:
    def __init__(self, page_source=None):
        print("created driver")
        self.page_source = page_source

    def __enter__(self):
        return self

    def get(self, url):
        print("calling mock get function")
        return self.page_source


@pytest.fixture
def driver(*args, **kwargs):
    def inner(*args, **kwargs):
        print("creating driver")
        driver = MockDriver(page_source=kwargs["page_source"])
        return driver
    return inner


def test_failed_driver(mocker):
    mocker.patch(
        "sylli_crawl.utils.driver_manager.init_driver",
        side_effect=WebDriverException("some exception")
    )
    # we expect a runtime error because the driver wont yield
    # Here we want to test to see if the driver doesnt raise
    # an UnboundLocalError by trying to close the driver after
    # a WebDriverException has been raised
    try:
        with driver_manager.get_driver() as driver:
            print("we have a driver")
            assert False
    except RuntimeError:
        assert True


def test_channel_name_found(mocker, mock_request, driver):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.consent",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.save_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.load_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.utils.driver_manager.get_driver"
    ).return_value.__enter__.return_value = MockDriver(
        page_source=mock_request("test-youtube-cp.html"))

    url = "https://some-website.com/some-path"
    js = js_crawler.YoutubeCrawler()
    parsed_html = js._request(url)
    actual_channel_name = js._channel_name(parsed_html)
    expected_channel_name = "Computerphile"
    assert actual_channel_name == expected_channel_name


def test_video_title_found(mocker, mock_request):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.consent",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.save_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.load_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.utils.driver_manager.get_driver"
    ).return_value.__enter__.return_value = MockDriver(
        page_source=mock_request("test-youtube-cp.html"))

    url = "https://some-website.com/some-path"
    js = js_crawler.YoutubeCrawler()
    parsed_html = js._request(url)
    actual_video_title = js._video_title(parsed_html)
    expected_video_title = "K-d Trees - Computerphile"
    assert actual_video_title == expected_video_title


def test_full_fetch(mocker, mock_request):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.consent",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.save_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.load_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.utils.driver_manager.get_driver"
    ).return_value.__enter__.return_value = MockDriver(
        page_source=mock_request("test-youtube-cp.html"))

    url = "https://some-website.com/some-path"
    js = js_crawler.YoutubeCrawler()
    actual_out = js.fetch(url)
    print(actual_out)
    expected_out = {
        "url": url,
        "title": "K-d Trees - Computerphile",
        "author": "Computerphile",
        "type": "V",
        "source": "https://some-website.com",
    }
    assert actual_out == expected_out


def test_youtube_request_on_remote_machine(mocker, mock_request):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.consent",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.save_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.js_crawler.YoutubeCrawler.load_cookies",
        return_value=None
    )
    mocker.patch(
        "sylli_crawl.utils.driver_manager.get_driver"
    ).return_value.__enter__.return_value = MockDriver(
        page_source=mock_request("test-youtube-on-debian.html"))

    url = "https://some-website.com/some-path"
    js = js_crawler.YoutubeCrawler()
    actual_out = js.fetch(url)
    print(actual_out)
    expected_out = {
        "url": url,
        "title": "RealestK -  SWM (Official Music video)",
        "author": "RealestK",
        "type": "V",
        "source": "https://some-website.com",
    }
    assert actual_out == expected_out
