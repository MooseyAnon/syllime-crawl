import pytest

from sylli_crawl import bing_crawler


def test_search_engine_results_found(mocker, response):
    mocker.patch(
        "sylli_crawl.bing_crawler.BingCrawler._request",
        return_value=response("test-bing.html")
    )
    bing_test = bing_crawler.BingCrawler()
    actual_out = bing_test.fetch("some query")
    # print(actual_out)
    expected_out = [
        "https://www.imdb.com/title/tt9418812/",
        "https://code.org/helloworld",
        "https://whatis.techtarget.com/definition/Hello-World",
        "https://www.tutorialspoint.com/cplusplus-hello-world-program",
        "https://www.learn-html.org/en/Hello%2C_World%21",
        "https://metrin.itch.io/hello-hello-world",
        "https://bloghr.wpengine.com/the-history-of-hello-world/",
        "https://www.geeksforgeeks.org/docker-hello-world/",
        "https://therenegadecoder.com/code/hello-world-in-powershell/",
        "https://www.helloworld.com.au/",
    ]
    assert actual_out == expected_out


def test_ensure_first_page_query_correctly_formed():
    b_crawler = bing_crawler.BingCrawler()
    actual_out = b_crawler.construct_query("some query 123")
    expected_out = "https://www.bing.com/search?q=some+query+123&first=1"
    assert actual_out == expected_out


def test_ensure_nth_page_query_correctly_formed():
    b_crawler = bing_crawler.BingCrawler()
    for i in range(1, 6):
        actual_out = b_crawler.construct_query("some query 123", page=i)
        page = (i * 10) - 9
        expected_out = "https://www.bing.com/" \
            f"search?q=some+query+123&first={page}"
        assert actual_out == expected_out


def test_headers_set_correctly():
    b_crawler = bing_crawler.BingCrawler()
    assert b_crawler.headers["Host"] == "www.bing.com" 
