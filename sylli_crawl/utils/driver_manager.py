"""Manage browser drivers."""

from contextlib import contextmanager
import logging

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger(__name__)

# browser height and width
WIDTH = "1920"
HEIGHT = "1080"


# reading if selenium gets clocked
# https://intoli.com/blog/not-possible-to-block-chrome-headless/

# ram issue on vm running firefox:
# stackoverflow.com/questions/55072731/selenium-using-too-much-ram-with-firefox
# stackoverflow.com/questions/
#   \63249385/selenium-automation-page-loading-is-very-slow
@contextmanager
def get_driver(headless=True):
    """Configure selenium drive.

    :yields: a selenium webdriver
    :raises WebDriverException: when webdriver cannot be initialised
    """
    # driver var placeholder
    driver = None
    # configure options for firefox browser
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
    # minimise resources required by firefox
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    try:
        driver = init_driver(
            options=options,
            executable_path="sylli_crawl/phantomjs/geckodriver",
        )
        yield driver

    except WebDriverException as e:
        logger.error("Webdriver Exception %s", e)

    finally:
        logger.info("Attempting to closing driver")
        if driver:
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