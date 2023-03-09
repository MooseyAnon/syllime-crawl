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
    # save this as a variable so we can log it
    number_of_pages = _globals.PAGES[choice]
    logger.info("Parsing %s pages", number_of_pages)
    return number_of_pages


def process_files(directory):
    """Process every file in a directory.

    This function loops through every file in a directory
    in order for it to be processed and renames them with a
    `_` prefix in order to signify that they have been successfully
    processed.

    :param pathlib.Path directory: the dir to process
    :yields: a pathlib.PosixPath object containing the next file
        to be processed
    """

    for file in directory.glob("*"):
        if not file.name.startswith("_"):
            yield file
            # rename file once processed
            new_file_name = f"_{file.name}"
            logger.info(
                "%s has been processed and will be renamed to %s",
                file.name, new_file_name)
            file.rename(directory / new_file_name)


def construct_search_result_object(query, results, meta_data):
    """Construct object containing search results.

    :param str query: the query that was searched on google/bing
    :param list results: the results from the search
    :param str meta_data: metadata associated with the search
    :returns: constructed data structure
    :rtype: dict
    """
    # shuffle result, this stops the chances of the same website directly
    # being listed one after the other. e.g. on both google and bing the
    # video results for a query are usually in the same area meaning you
    # are likely to get multiple youtube/vimeo links in a row. we want to
    # minimise this from happening so we dont get blocked by the website
    random.shuffle(results)  # shuffles in place
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

    # we need a unique key
    key = data["query"]
    if key in pre_existing_data:
        logger.info("%s --> already exists in data", key)

    # update and save
    pre_existing_data.update({key: data})
    helpers.write_json(pre_existing_data, path)


def update_resource_data(path, data, key):
    """Update resource JSON data.

    This is to update the file containing the eventual
    data that will be fed to the backend.

    :param pathlib.Path path: the path to JSON file
    :param dict data: data to write to file
    :param str key: key to save data under
    """
    if path.exists():
        pre_existing = helpers.read_json(path)
    else:
        pre_existing = {key: []}

    # Do we need the key? Each file only has one key in the dict
    pre_existing[key].append(data)
    helpers.write_json(pre_existing, path)


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
                        helpers.wait(end=500)
                # the directory the final resource information will live
                meta_data = (
                    f"{course_data['course']}/{level['level']}/"
                    f"{module['module']}"
                ).strip()
                yield construct_search_result_object(
                    topic.strip(), list(results), meta_data)


def course_processor(full_path, dry_run=False):
    """Process a course.

    Give a JSON file containing course modules and topics to
    search google/bing for resources.

    :param pathlib.Path full_path: path to file containing course data.
    :param bool dry_run: dry run flag
    :returns: 0 if successful - meaning script completed not search
        engines have been crawled successfully
    :rtype: int
    """
    course_data = helpers.read_json(full_path)
    if not course_data:
        return 1

    for output in process(course_data, dry_run=dry_run):
        if not dry_run:
            # the path in the search dir we want to save the data to
            path_to_search = _globals.SEARCH_RESULT_OUT_FOLDER / full_path.name
            update_save_json(path_to_search, output)

    return 0


def search_results_processor(full_path, dry_run=False):
    """Process search results file.

    This parses the output of a crawled search engine. These
    live in the 'search-results' dir.

    :param str full_path: path to file containing the search results
    :param bool dry_run: dry run flag
    :return: 0 if successful - meaning the script completed, not that
        all URLs have been successfully fetched
    :rtype: int
    """
    search_res = helpers.read_json(full_path)
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
        # discovered URLs for a topic will be saved to a file
        full_resource_path = (
            _globals.RESOURCES_OUT_FOLDER / res_data["meta-data"])
        helpers.mkdir(full_resource_path)
        for index in range(last_dicovered_index + 1, len(results)):
            # fetch url information
            data = fetch_url(results[index], dry_run=dry_run)
            if data:
                # incrementally update file in case we crash mid way
                update_resource_data(
                    (
                        full_resource_path
                        / res_data["query"].strip().replace(" ", "-")
                    ),
                    data, res_data["query"]
                )
            # increment last discovered and save back to query file
            # in case the program crashes before finishing
            # we want to do this even if there is an error as we will deal
            # with errors later
            res_data["last-discovered"] += 1
            update_save_json(full_path, res_data)

            # we still want to slow down the crawlers as there may be
            # several consecutive links to the same website e.g. youtube
            if not dry_run:
                helpers.wait()
    return 0


def dispatch(directory, filename=None, dry_run=False):
    """Process a file or directory.

    This dispatches either a search engine crawler or a
    regular crawler depending on the chosen directory.

    :param str directory: name of directory to process files from
    :param str filename: a filename to process instead of a while directory
    :param bool dry_run: run tool in dry run mode

    :returns: 0 if successful - meaning the script completed, not that
        all URLs have been successfully fetched
    :rtype: int
    """
    if directory not in ("search", "query"):
        logger.error("directory must be one of: [search, query]")
        return 1

    # process the outcome of google/bing crawler
    if directory == "search":
        logger.info("parsing processing search results")
        dir_path = _globals.SEARCH_RESULT_OUT_FOLDER
        func = search_results_processor

    # input to google/bing crawler i.e. curriculums
    if directory == "query":
        logger.info("processing queries")
        dir_path = _globals.QUERY_FOLDER
        func = course_processor

    res = 0
    # only process one file
    if filename:
        logger.info("processing single file %s", filename)
        full_path = dir_path / filename
        res = func(full_path, dry_run=dry_run)

    else:
        # go through full dir
        for fullpath in process_files(dir_path):
            logger.info("Processing file from dir, filename: %s", fullpath)
            res = func(fullpath, dry_run=dry_run)
            if res != 0:
                logger.error(
                    "there was an issue processing %s, returning early",
                    fullpath
                )
                break

    return res
