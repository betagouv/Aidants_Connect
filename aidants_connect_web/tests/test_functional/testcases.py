from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.webdriver import WebDriver


class FunctionalTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        firefox_options = FirefoxOptions()
        firefox_options.headless = settings.HEADLESS_FUNCTIONAL_TESTS

        cls.selenium = WebDriver(options=firefox_options)
        cls.selenium.implicitly_wait(10)

        # In some rare cases, the first connection to the Django LiveServer
        # fails for reasons currently unexplained. Setting this variable to `True`
        # enables a quick and dirty workaround that launches a first connection
        # and ignores its potential failure.
        if settings.BYPASS_FIRST_LIVESERVER_CONNECTION:
            try:
                cls.selenium.get(f"{cls.live_server_url}/")
            except WebDriverException:
                pass

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def open_live_url(self, url):
        """Helper method to trigger a GET request on the Django live server."""

        self.selenium.get(f"{self.live_server_url}{url}")
