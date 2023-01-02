"""The main CLI crawler runner."""
import argparse
import logging.config
import pathlib

from . import _api as api


def cli():
    """Parse command line arguments

    :return: parsed CLI args
    :rtype: argsparse.Namespace
    """
    # parser to define common shared arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--dry-run", action="store_true")

    # main parser
    parser = argparse.ArgumentParser(
        prog="crawl", description="SylliMe Crawler")

    subparsers = parser.add_subparsers(
        help="usage: crawl <command> <args>")

    # search engine crawler
    se_parser = subparsers.add_parser(
        "search-engine",
        parents=[common_parser],
        help="Scrape google, bing or both, for a given query",
    )
    se_parser.add_argument(
        "--query-file",
        type=pathlib.Path,
        help="File containing query data",
    )
    se_parser.set_defaults(func=api.course_processor)

    # web crawler
    web_parser = subparsers.add_parser(
        "web-crawler",
        parents=[common_parser],
        help="Scrape web pages for title and other metadata",
    )
    web_parser.add_argument(
        "--resource-file",
        type=pathlib.Path,
        help="File containing URLs for course resources",
    )
    web_parser.set_defaults(func=api.search_results_processor)
    return parser.parse_args()


if __name__ == "__main__":
    # set the logging config file
    # disable_existing_logger=False param is to make sure any pre-existing
    # loggers in the program are able to run
    # this is useful when logging in different modules as it is not always
    # clear which logger gets created first
    # more info:
    # - docs.python.org/3/library/logging.config.html#logging.config.fileConfig
    logging.config.fileConfig("logging.ini", disable_existing_loggers=False)
    args = cli()
    print(args)
    args.func(args.resource_file, args.dry_run)
    # args.func(args.query_file, args.dry_run)
    # sys.exit(arguments.func(arguments))
    # contents = read_json(QUERY_FOLDER / args.query_file)
    # import pprint
    # pprint.pprint(contents)

    # course_processor(QUERY_FOLDER / args.query_file)
