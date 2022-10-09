import pytest

from sylli_crawl import js_crawler


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
        "sylli_crawl.js_crawler.get_driver"
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
        "sylli_crawl.js_crawler.get_driver"
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
        "sylli_crawl.js_crawler.get_driver"
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
