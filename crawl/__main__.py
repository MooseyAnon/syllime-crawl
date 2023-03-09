"""The main CLI crawler runner."""
import argparse
import logging.config
import pathlib
import sys

from . import _api as api


def cli():
    """Parse command line arguments

    :return: parsed CLI args
    :rtype: argsparse.Namespace
    """
    parser = argparse.ArgumentParser(
        prog="crawl", description="SylliMe Crawler")

    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing files to process. Options are: "
             "query or search"
    )
    parser.add_argument(
        "--file",
        type=pathlib.Path,
        help="File containing querys or course resources. If given only "
             "only that file will be processed",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run program in dry-run mode"
    )
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
    sys.exit(api.dispatch(args.directory, args.file, args.dry_run))
