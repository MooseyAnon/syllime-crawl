"""The APIs used by the crawlers."""
import logging
import random

from sylli_crawl.utils import helpers
from . import _globals

logger = logging.getLogger(__name__)


def pages():
    """Randomly select the number of search engine pages to crawl.

    We want to do this to minimise any unformity during runtime i.e.
    if we always crawl the first 3 pages of every query it becomes
    obvious that this is an automated process potenitally leading to
    a CAPTCHA from one of the search engines.

    :returns: the number of pages to crawl for each query
    :rtype: int
    """
    # pick a random number of pages to query
    choice = random.choice(range(1, 102)) % len(_globals.PAGES)
    return _globals.PAGES[choice]


def construct_search_result_object(query, results, meta_data):
    """Construct object containing search results.

    :param str query: the query that was searched on google/bing
    :param list results: the results from the search
    :param str meta_data: metadata associated with the search
    :returns: constructed data structure
    :rtype: dict
    """
    obj = {
        "query": query,
        "meta-data": meta_data,
        "search-results": results,
        # the index of the last discovered url,
        # this will be used later by the web crawlers
        # to save crawl progress
        "last-discovered": -1,
    }
    return obj


def update_save_json(path, data):
    """Update and save JSON.

    Attempts to update a pre-existing JSON file or
    creates a new one if not already present.

    :param pathlib.Path path: location to save the data
    :param dict data: data to be saved
    """
    # incase there is not pre-existing data
    pre_existing_data = {}
    if path.exists():
        pre_existing_data = helpers.read_json(path)

    # we need a unique key for each topic so we can just use topic name
    key = data["query"]
    if key in pre_existing_data:
        logger.warning("%s --> already exists in data", key)
        return

    # update and save
    pre_existing_data.update({key: data})
    helpers.write_json(pre_existing_data, path)


def fetch_query(query, result_set, page, dry_run=False):
    """Fetch a search engine query.

    :param str query: the query to fetch
    :param set result_set: the set to save fetched URLS
    :param int page: the page number to fetch
    :param bool dry_run: dry run flag

    :returns: a set containing fetch urls
    :rtype: set(str)
    """

    for se in _globals.CRAWLERS["engines"]:
        results = se.fetch(query, page=page, dry_run=dry_run)
        if results and not dry_run:
            # this makes sure we dont get duplicate resources
            for result in results:
                result_set.add(result)

    return result_set


def fetch_url(url, dry_run=False):
    """Fetch a URL using a web crawler.

    :param str url: the URL to fetch
    :param bool dry_run: dry run flag
    :return: fetched data
    :rtype: dict(str, str)
    """
    # exit early if url is a pdf or an instagram page
    # as we're unable to crawl those atm
    if url.endswith("pdfs"):
        logger.warning("cannot parse, URL is a PDF: %s", url)
        return {}

    if "instagram" in url:
        logger.warning("cannot parse, URL is an instagram page: %s", url)
        return {}

    if "youtube" in url or "khan" in url:
        crawler = _globals.CRAWLERS["web"]["js"]

    else:
        crawler = _globals.CRAWLERS["web"]["html"]

    return crawler.fetch(url, dry_run=dry_run)


def process(course_data, dry_run=False):
    """Process course data.

    :param dict course_data: structure containing course information
        to be processed
    :param bool dry_run: dry run flag
    :yields dict: processed data for one topic
    """
    for level in course_data["levels"]:
        for module in level["modules"]:
            for topic in module["topics"]:
                results = set()
                for page in range(1, pages() + 1):
                    # fetch
                    results = fetch_query(topic, results, page, dry_run=dry_run)
                    if not dry_run:
                        helpers.wait(end=120)
                # the directory the final resource information will live
                meta_data = (
                    f"{course_data['course']}/{level['level']}/"
                    f"{module['module']}"
                )
                yield construct_search_result_object(
                    topic, list(results), meta_data)


def course_processor(file_name, dry_run=False):
    """Process a course.

    Give a JSON file containing course modules and topics
    search google/bing for resources.

    :param pathlib.Path file_name: file containing course data.
    :param bool dry_run: dry run flag
    :returns: 0 if successful - meaning script completed not search
        engines have been crawled successfully
    :rtype: int
    """
    course_data = helpers.read_json(_globals.QUERY_FOLDER / file_name)
    if not course_data:
        return 1

    for output in process(course_data, dry_run=dry_run):
        if not dry_run:
            update_save_json(
                _globals.SEARCH_RESULT_OUT_FOLDER / file_name,
                output
            )

    return 0


def search_results_processor(file_name, dry_run=False):
    """Process search results file.

    This parses the output of a crawled search engine. These
    live in the 'search-results' dir.

    :param str file_name: the file containing the search results
    :param bool dry_run: dry run flag
    :return: 0 if successful - meaning the script completed, not that
        all URLs have been successfully fetched
    :rtype: int
    """
    search_res = helpers.read_json(
        _globals.SEARCH_RESULT_OUT_FOLDER / file_name)
    if not search_res:
        return 1

    for query in search_res.keys():
        res_data = search_res[query]
        results = res_data["search-results"]
        last_dicovered_index = res_data["last-discovered"]
        logger.info(
            "query: %s - (start index): %s",
            res_data["query"],
            last_dicovered_index + 1
        )
        data_to_save = []
        for result in range(last_dicovered_index + 1, len(results)):
            # fetch url information
            data = fetch_url(results[result], dry_run=dry_run)
            # print(data)
            # print("------")
            data_to_save.append(data)

            # increment last discovered and save back to query file
            # in case the program crashes before finishing
            res_data["last-discovered"] += 1

            # we still want to slow down the crawlers as there may be
            # several consecutive links to the same website e.g. youtube
            if not dry_run:
                helpers.wait()

        # once all urls for a topic have been discovered saved to file
        full_resource_path = (
            _globals.RESOURCES_OUT_FOLDER / res_data["meta-data"]
        )
        helpers.mkdir(full_resource_path)
        helpers.write_json(
            {res_data["query"]: data_to_save},
            full_resource_path / res_data["query"]
        )
    return 0
