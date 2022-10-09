import pytest

from sylli_crawl import google_crawler


def test_search_engine_results_found(mocker, response):
    mocker.patch(
        "sylli_crawl.google_crawler.GoogleCrawler._request",
        return_value=response("test-google.html")
    )
    google_test = google_crawler.GoogleCrawler()
    actual_out = google_test.fetch("some query")
    expected_out = [
        "https://www.nba.com/warriors/",
        "http://www.nba.com/warriors/",
        "https://en.wikipedia.org/wiki/Golden_State_Warriors",
        "h?hl=en-GB",
        "https://www.foxsports.com/nba/golden-state-warriors-team-roster",
        "https://www.foxsports.com/nba/golden-state-warriors-team-roster",
        "https://www.foxsports.com/nba/golden-state-warriors-team-roster",
        "https://www.nba.com/team/1610612744/warriors",
        "https://www.nba.com/team/1610612744/warriors",
        "https://www.nba.com/team/1610612744/warriors",
        "https://www.barrystickets.com/blog/golden-state-warriors-name/",
        "https://www.barrystickets.com/blog/golden-state-warriors-name/",
        "https://en.wikipedia.org/wiki/Golden_State_Warriors",
        "http://en.wikipedia.org/wiki/Western_Conference_(NBA)",
        "https://www.espn.co.uk/nba/team/_/name/gs/golden-state-warriors",
        "https://www.goldenstateofmind.com/",
        "https://www.npr.org/2022/01/17/1073705516/co-owner-of-the-nbas-warriors-lambasted-after-saying-nobody-cares-about-the-uygh",
        "https://www.dailymail.co.uk/news/article-10412639/Silicon-Valley-billionaire-Golden-State-Warriors-Chamath-Palihapitiya-cowardly-Uyghur-Muslims.html",
        "https://bleacherreport.com/golden-state-warriors",
        "https://www.instagram.com/warriors/%3Fhl%3Den",
    ]
    assert actual_out == expected_out


def test_ensure_first_page_query_correctly_formed():
    g_crawler = google_crawler.GoogleCrawler()
    actual_out = g_crawler.construct_query("some query 123")
    expected_out = "https://www.google.com/" \
        "search?q=some+query+123&start=0&safe=strict&ie=UTF-8"
    assert actual_out == expected_out


def test_ensure_nth_page_query_correctly_formed():
    g_crawler = google_crawler.GoogleCrawler()
    for i in range(1, 6):
        actual_out = g_crawler.construct_query("some query 123", page=i)
        page = (i - 1) * 10
        expected_out = (
            "https://www.google.com/"
            f"search?q=some+query+123&start={page}"
            "&safe=strict&ie=UTF-8"
        )
        assert actual_out == expected_out


def test_headers_set_correctly():
    g_crawler = google_crawler.GoogleCrawler()
    assert g_crawler.headers["Sec-Fetch-Site"] == "same-origin"


def test_modal_page(mocker, response):
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "sylli_crawl.google_crawler.GoogleCrawler._request",
        return_value=response("test-google-modal.html", 204)
    )
    g_crawler = google_crawler.GoogleCrawler()
    actual = g_crawler.fetch("hello world")
    assert actual == [
        "https://en.wikipedia.org/wiki/%22Hello,_World!%22_program",
        "https://helloworld.raspberrypi.org/",
        "https://code.org/helloworld",
        "https://www.imdb.com/title/tt21617580/",
        "https://www.imdb.com/title/tt9418812/",
        "https://www.projecthelloworld.org/",
        "https://www.programiz.com/c-programming/examples/print-sentence",
        "https://www.youtube.com/watch?v=Yw6u6YkTgQ4",
        "https://www.youtube.com/watch?v=u7JMhVI7taQ",
        "https://www.youtube.com/watch?v=a25_gGnmJAw"
    ]


def test_build_consent_url():
    g_crawler = google_crawler.GoogleCrawler()
    consent_url = "https://consent.google.com/save"
    badly_formatted_str = (
        "https://consent.google.com/save?continue=https://www.google.com/"
        "search?q%3Dhello%2Bworld&gl=GB&m=0&pc=srp&x=5&src=2&hl=en&"
        "bl=gws_20220913-0_RC1&uxe=none&set_eom=false&set_aps=true&set_sc=tru"
    )
    expected_str = (
        "https://consent.google.com/save?continue=https://www.google.com/"
        "search?q%3Dhello%2Bworld&gl=GB&m=0&pc=srp&x=5&src=2&hl=en&"
        "bl=gws_20220913-0_RC1&uxe=none&set_eom=true"
    )
    out = g_crawler._build_consent_url(badly_formatted_str)
    assert f"{consent_url}?{out}" == expected_str


def test_find_video(mock_request):
    g_crawler = google_crawler.GoogleCrawler()
    bs4_obj = g_crawler._create_bs4_obj(mock_request("test-google-modal.html"))
    expected = [
        "https://www.youtube.com/watch?v=Yw6u6YkTgQ4",
        "https://www.youtube.com/watch?v=u7JMhVI7taQ",
        "https://www.youtube.com/watch?v=a25_gGnmJAw"
    ]
    assert g_crawler.parse_video(bs4_obj) == expected
