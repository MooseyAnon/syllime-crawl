import pytest

from sylli_crawl import html_crawler


def test_title_found(mocker, response):
    mocker.patch(
        "sylli_crawl.html_crawler.HTMLCrawler._request",
        return_value=response("test-html-crawler.html")
    )
    url = "https://some-website.com/some-path"
    html = html_crawler.HTMLCrawler()
    actual_out = html.fetch(url)
    expected_out = {
        "url": url,
        "title": "Meat Loaf: " \
            "Lorraine Crosby pays tribute to 'great man' - BBC News",
        "author": "some-website.com",
        "type": "A",
        "source": "some-website.com",
    }
    assert actual_out == expected_out
