"""Global objects for commandline tool."""
import os
import pathlib

from sylli_crawl import bing_crawler, google_crawler, html_crawler, js_crawler

# various folder/file locations to use at runtime as Path objects
QUERY_FOLDER = pathlib.Path(os.environ.get("QUERY_FOLDER", "files/querys"))
RESOURCES_OUT_FOLDER = pathlib.Path(
    os.environ.get("RESOURCES_OUT_FOLDER", "files/resources"))
SEARCH_RESULT_OUT_FOLDER = pathlib.Path(
    os.environ.get("SEARCH_RESULT_OUT_FOLDER", "files/search-results"))

# we want to keep uniformity at a minimum when it comes to search engine
# scarpping. This means not always looking up the same number of pages for
# every query to a search engine. We'll randomly pick a number from this array
# for each query we search.
PAGES = [1, 2, 3]

# init crawler so we can keep using the same session across requests
CRAWLERS = {
    "engines": [
        bing_crawler.BingCrawler(),
        google_crawler.GoogleCrawler(),
    ],
    "web": {
        "html": html_crawler.HTMLCrawler(),
        "js": js_crawler.JavascriptCrawler(),
    }
}
