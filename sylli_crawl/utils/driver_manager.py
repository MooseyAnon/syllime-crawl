"""Manage browser drivers."""

from contextlib import contextmanager
import logging

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger(__name__)

# browser height and width
WIDTH = "1920"
HEIGHT = "1080"


# https://stackoverflow.com/questions/15645093/setting-request-headers-in-selenium
# https://stackoverflow.com/questions/15397483/how-do-i-set-browser-width-and-height-in-selenium-webdriver
@contextmanager
def get_driver(headless=True):
    """Configure selenium drive.

    :yields: a selenium webdriver
    :raises WebDriverException: when webdriver cannot be initialised
    """
    options = webdriver.FirefoxOptions()
    # set browser headless state
    options.headless = headless
    logger.info(
        "set driver headless state to %s",
        headless
    )
    # add width and height
    options.add_argument(f"--width={WIDTH}")
    options.add_argument(f"--height={HEIGHT}")
    # set log level, we want to minimise noise
    options.add_argument("--log-level=3")
    try:
        driver = init_driver(
            options=options,
            executable_path="sylli_crawl/phantomjs/geckodriver",
        )
        yield driver

    except WebDriverException as e:
        logger.error("webdriver exception: %s", e)

    finally:
        logger.info("closing driver")
        driver.close()
        driver.quit()


def init_driver(*args, **kwargs):
    """Initialise Firefox web driver.

    :param tuple args: list of arguments to pass to driver
    :param dict kwargs: keyword arguments to pass to driver
    :returns: a Firefox web browser driver
    :rtype: selenium.webdriver
    """
    driver = webdriver.Firefox(*args, **kwargs)
    return driver
