from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait


@override_settings(DEBUG=True)
class FunctionalTestCase(StaticLiveServerTestCase):
    js = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        firefox_options = FirefoxOptions()
        firefox_options.headless = settings.HEADLESS_FUNCTIONAL_TESTS
        firefox_options.set_preference("javascript.enabled", cls.js)

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

    def admin_login(self, user: str, password: str, otp: str):
        selenium_wait = WebDriverWait(self.selenium, 10)

        path = reverse("otpadmin:login")
        self.open_live_url(path)
        selenium_wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(By.CSS_SELECTOR, 'input[name="username"]').send_keys(
            user
        )
        self.selenium.find_element(By.CSS_SELECTOR, 'input[name="password"]').send_keys(
            password
        )
        self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="otp_token"]'
        ).send_keys(otp)

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        selenium_wait.until(url_matches(f"^.+{reverse('otpadmin:index')}$"))
