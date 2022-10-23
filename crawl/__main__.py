# pylint: disable = unspecified-encoding
"""The main CLI crawler runner."""
import argparse
import csv
import json
import logging
import logging.config
import pathlib
import random
import time
import sys

from sylli_crawl import bing_crawler, google_crawler, html_crawler, js_crawler


SEARCH_RESULT_OUT_FOLDER = pathlib.Path("files/search-results")
QUERY_FOLDER = pathlib.Path("files/querys")
ENGINES = {
    "bing": bing_crawler.BingCrawler,
    "google": google_crawler.GoogleCrawler,
}

# set the logging config file
logging.config.fileConfig("logging.ini")
logger = logging.getLogger("crawl")


def fetch_query(query, result_set, engines, pages=1):
    """Fetch a search query for a given search engine.

    :param str query: the query to search
    :param set result_set: set to save unique harvested URLs
    :param list engines: a list of engines to query
    :param int pages: the number of pages to fetch for each search engine

    :return: a set of unique URLs
    :rtype: set(str)
    """
    for page in range(1, pages + 1):
        logger.info("fetching page: %s", page)
        for search_engine in engines:
            res = search_engine.fetch(query, page=page)
            if res:
                for r in res:
                    result_set.add(r)
        wait()
    return result_set


def write_query(query, res_set):
    """Write harvested URLs for a given query to a file.

    :param str query: the original query, will be used in file descriptor
    :param set res_set: the URLs
    :return: 0 if  write opertation success else 1
    :rtype: int
    """
    exit_status = 0
    # get rid of any preceeding or trailing whitespace
    query = query.strip()
    write_file_descriptor = (
        SEARCH_RESULT_OUT_FOLDER / f'{"-".join(query.split(" "))}-tmp.txt'
    )
    mode = "w"
    if write_file_descriptor.exists():
        mode = "a"

    try:
        with open(write_file_descriptor, mode) as wf:
            writer = csv.writer(wf)
            for line in res_set:
                writer.writerow([line])
    except OSError as e:
        logger.error(e)
        exit_status = 1

    return exit_status


def wait(start=6, end=45):
    """Wait for a random time period chosen from a range.

    :param int start: start of the range
    :param int end: endo of the range
    """
    sleep_time = random.choice(range(start, end))
    logger.info("sleeping for %s", sleep_time)
    time.sleep(sleep_time)


def read_querys_file(query_file):
    """Read a file.

    :param str query_file: file to read
    :returns: contents of file saved in memory
    :rtype: str
    """
    contents = None
    with open(query_file, "r") as rf:
        contents = rf.readlines()
    return contents


def search_engine_crawler(args):
    """Initiate the search engine crawler.

    :param argsparse.Namespace args: an argsparse namespace
    :returns: the exit status of the operation, 0 for success 1 if not
    :rtype: int
    """
    if not args.query and not args.query_file:
        logger.error("query or query file required")
        return 1

    if args.query and args.query_file:
        logger.error("query cannot be used in conjunction with query file")
        return 1

    if args.query_file and not (QUERY_FOLDER / args.query_file).exists():
        logger.error("query file does not exist")
        return 1

    if args.search_engine and args.search_engine not in ENGINES:
        logger.error("search engine must be google or bing")
        return 1

    if args.pages < 1:
        logger.error("must have one or more pages")
        return 1

    # init crawlers and add to arr
    # we need to init to maintain headers/cookies across requests
    engines = []
    if args.search_engine:
        engines.append(ENGINES[args.search_engine]())

    else:
        for search_engine in ("bing", "google"):
            engines.append(ENGINES[search_engine]())

    # start parsing/fetching querys from file
    if args.query_file:
        full_path = QUERY_FOLDER / args.query_file
        querys = read_querys_file(full_path)
    # a single query to fetch
    else:
        querys = [args.query]

    for query in querys:
        # process query
        result_set = fetch_query(query, set(), engines, pages=args.pages)
        # write results to file
        write_query(query, result_set)
        # we want to slow the crawler down so search engines
        # do not block us
        wait()

    return 0


def web_crawler(args):
    """Initialise none search engine crawlers.

    :param argsparse.Namespace args: an argsparse namespace
    :returns: the exit status of the operation, 0 for success 1 if not
    :rtype: int
    """
    if args.link_file and not args.link_file.exists():
        logger.error("link file does not exist")
        return 1

    if args.link_file and args.url:
        logger.error("cannot have both a link file and a url")
        return 1

    if not args.link_file and not args.url:
        logger.error("you need either a link file or a url to scrape")
        return 1

    # init crawler singletons
    html = html_crawler.HTMLCrawler()
    js = js_crawler.JavascriptCrawler()

    # open file and read line, dispatch to appropriate crawler
    # and append to output arr
    output_arr = []
    if args.link_file:
        with open(args.link_file, "r") as rf:
            reader = csv.reader(rf)

            for url in reader:

                if "youtube" in url or "khanacademy" in url:
                    out = js.fetch(url)

                elif url.endswith(".pdf"):
                    logger.warning("currently unable to parse PFDs")

                else:
                    out = html.fetch(url)

                output_arr.append(out)
    else:

        if "youtube" in args.url or "khanacademy" in args.url:
            out = js.fetch(args.url)

        elif args.url.endswith(".pdf"):
            logger.warning("currently unable to parse PFDs")

        else:
            out = html.fetch(args.url)

    # write output arr to a json file
    write_fd = f"{args.link_file}-out.json"
    with open(write_fd, "w") as wf:
        # save with file name as key
        # file name should be the topic title
        to_dump = {f"{args.link_file}.json": output_arr}
        json.dump(to_dump, wf)

    return 0


def cli():
    """Parse command line arguments

    :return: parsed CLI args
    :rtype: argsparse.Namespace
    """
    parser = argparse.ArgumentParser(
        prog="crawl", description="SylliMe Crawler")

    subparsers = parser.add_subparsers(
        help="usage: crawl <command> <args>")

    # search engine crawler
    se_parser = subparsers.add_parser(
        "search-engine", help="Scrape google, bing or both, for a given query"
    )
    se_parser.add_argument(
        "--query", type=str,
        help="query to scrape for, cannot be used with query file"
    )
    se_parser.add_argument(
        "--query-file", type=pathlib.Path,
        help="file containing querys"
    )
    se_parser.add_argument(
        "--search-engine", type=str,
        help="search engine to scrape, leave empty for both engines"
    )
    se_parser.add_argument(
        "--pages", type=int, default=1,
        help="number of result pages to scrape "
        "i.e. 5 will return 5 pages of results"
    )
    se_parser.set_defaults(func=search_engine_crawler)

    # webcrawler for crawling non search engine sites
    web_parser = subparsers.add_parser(
        "web", help="Scrape a given file of URLS or a single URL for metadata"
    )
    web_parser.add_argument(
        "--link-file", type=pathlib.Path, help="path to file containing links"
    )
    web_parser.add_argument(
        "--url", type=str, help="a singular url to scrape"
    )
    web_parser.add_argument(
        "--get-test-page", action="store_true",
        help="grab html for a test page"
    )
    web_parser.set_defaults(func=web_crawler)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = cli()
    sys.exit(arguments.func(arguments))
