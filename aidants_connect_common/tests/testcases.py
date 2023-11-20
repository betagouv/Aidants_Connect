import re
from typing import Optional
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_web.models import Aidant


@override_settings(DEBUG=True)
class FunctionalTestCase(StaticLiveServerTestCase):
    js = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        firefox_options = FirefoxOptions()

        firefox_options.headless = settings.HEADLESS_FUNCTIONAL_TESTS
        if settings.HEADLESS_FUNCTIONAL_TESTS:
            firefox_options.add_argument("--headless")

        firefox_options.set_preference("javascript.enabled", cls.js)

        cls.selenium = WebDriver(options=firefox_options)
        cls.selenium.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.selenium, 10)

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

    def login_aidant(self, aidant: Aidant, otp_code: str | None = None):
        """
        This method is meant to replace
        ``aidants_connect_web.tests.test_functional.utilities`` and avoid the burden
        of creating a known OTP code each time. The first found token will be used.
        Optionnaly, another OTP code can be specified.
        """
        otp_code = otp_code or aidant.staticdevice_set.first().token_set.first().token

        login_field = self.selenium.find_element(By.ID, "id_email")
        login_field.send_keys(aidant.email)
        otp_field = self.selenium.find_element(By.ID, "id_otp_token")
        otp_field.send_keys(otp_code)
        submit_button = self.selenium.find_element(
            By.CSS_SELECTOR, "input[type='submit']"
        )
        submit_button.click()
        self.wait.until(self.path_matches("magicauth-email-sent"))
        self.assertEqual(len(mail.outbox), 1)
        url = (
            re.findall(r"https?://\S+", mail.outbox[0].body, flags=re.M)[0]
            .replace("https", "http", 1)
            .replace("chargement/code", "code", 1)
        )
        self.selenium.get(url)

    def path_matches(
        self, route_name: str, *, kwargs: dict = None, query_params: dict = None
    ):
        kwargs = kwargs or {}
        query_part = urlencode(query_params or {}, quote_via=lambda s, _1, _2, _3: s)
        query_part = rf"\?{query_part}" if query_part else ""
        return url_matches(
            rf"http://localhost:\d+{reverse(route_name, kwargs=kwargs)}{query_part}"
        )

    def assertElementNotFound(self, by=By.ID, value: Optional[str] = None):
        implicit_wait = self.selenium.timeouts.implicit_wait
        self.selenium.implicitly_wait(0.1)
        try:
            with self.assertRaises(
                NoSuchElementException, msg="Found element expected to be absent"
            ):
                self.selenium.find_element(by=by, value=value)
        finally:
            self.selenium.implicitly_wait(implicit_wait)
