import contextlib
import operator
import os
import re
import time
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.db import models
from django.test import tag
from django.urls import reverse

from axe_selenium_python import Axe
from faker.proxy import Faker
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_web.models import Aidant

DefaultGetter = Callable[[models.Model | Mapping, str], Any]
CustomGetter = Callable[[models.Model | Mapping, str, DefaultGetter], Any]


@tag("functional")
class FunctionalTestCase(StaticLiveServerTestCase):
    js = True
    faker = Faker()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        firefox_options = FirefoxOptions()

        firefox_options.headless = settings.HEADLESS_FUNCTIONAL_TESTS
        if settings.HEADLESS_FUNCTIONAL_TESTS:
            firefox_options.add_argument("--headless")

        # Allow pasting in console
        firefox_options.set_preference("devtools.selfxss.count", 1_000_000)
        firefox_options.set_preference("javascript.enabled", cls.js)

        service = Service(
            log_output="./geckodriver.log", service_args=["--log", "debug"]
        )
        cls.selenium = WebDriver(options=firefox_options, service=service)
        cls.selenium.implicitly_wait(3)
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

        # Initialize accessibility testing tools
        cls.axe = None
        cls._axe_injected = False

        # Monkey-patch WebDriver to slow down functional test execution in browser
        # useful to debug if HEADLESS_FUNCTIONAL_TESTS is True
        if os.getenv("HEADLESS_FUNCTIONAL_TESTS") == "False":
            delay = 0.5

            def slow_command_executor(self, *args, **kwargs):
                result = self._original_execute(*args, **kwargs)
                time.sleep(delay)
                return result

            cls.selenium._original_execute = cls.selenium.execute
            cls.selenium.execute = slow_command_executor.__get__(
                cls.selenium, type(cls.selenium)
            )

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def open_live_url(self, url):
        """Helper method to trigger a GET request on the Django live server."""
        self.selenium.get(f"{self.live_server_url}{url}")
        self.wait.until(self.document_loaded())

    def admin_login(self, user: str, password: str, otp: str):
        self.open_live_url(reverse("otpadmin:login"))
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

        self.wait.until(self.document_loaded())

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
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, "[type='submit']")
        submit_button.click()
        self.wait.until(self.path_matches("magicauth-email-sent"))
        self.assertEqual(len(mail.outbox), 1)
        url = (
            re.findall(r"https?://\S+", mail.outbox[0].body, flags=re.M)[0]
            .replace("https", "http", 1)
            .replace("chargement/code", "code", 1)
        )
        self.selenium.get(url)

    def fill_form(
        self,
        data: models.Model | Mapping,
        fields: forms.Form | Iterable[forms.BoundField],
        custom_getter: CustomGetter | None = None,
        selector: WebElement = None,
    ):
        """
        Generic method to fill a form in a page using Selenium with provided data

        fields: form fields to fill in the page. Can be passed a Form, in which case
                every field in :attr:`django.forms.forms.Form.visible_fields()` will be
                filled. Pass a list of :class:`django.forms.forms.BoundField` to
                customize which fields to fill.

        data: the data to fill the form with. Can be an instance of
              :class:`django.db.models.Model` or a simple dict.

        custom_getter: a callable that takes
                       (:param:`data`, :param:`fields`, :param:`default_getter`)
                       as parameters where ``data`` and ``fields`` are the same ones
                       passed to ``fill_form`` and ``default_getter`` is the default
                       callable used to retieve data from objects.

        example:

        >>> from aidants_connect_web.tests.factories import HabilitationRequestFactory
        ... from aidants_connect_web.forms import HabilitationRequestCreationForm
        ...
        ... def my_getter(obj, name, provided_getter):
        ...     return (
        ...         default_getter(obj, "course_type" )
        ...         if name === "type"
        ...         else provided_getter(obj, name)
        ...     )

        >>> the_data = HabilitationRequestFactory.build()
        ... the_fields = HabilitationRequestCreationForm().visible_fields()
        ... self.fill_form(the_data, the_fields, my_getter)
        """
        selector = selector or self.selenium

        actual_fields = list(
            fields.visible_fields() if isinstance(fields, forms.Form) else fields
        )
        default_getter: DefaultGetter = (
            operator.getitem if isinstance(data, Mapping) else getattr
        )

        val_getter: DefaultGetter = default_getter
        if custom_getter:

            def wrapped_getter(_data, _name):
                return custom_getter(_data, _name, default_getter)

            val_getter = wrapped_getter

        if len(actual_fields) == 0:
            self.fail("No fillable fields were provided")

        if not isinstance(actual_fields[0], forms.BoundField):
            self.fail(
                "Provided fields are not BoundField instances; use `form[field_name]` "
                "of `form.visible_fields()` instead of `form.fields[field_name]`."
            )

        for bf in actual_fields:
            if isinstance(bf.field.widget, forms.Select):
                value = bf.field.prepare_value(val_getter(data, bf.name))
                if value is None:
                    self.fail(
                        f"Couldn't translate {bf.name} from data into a "
                        f"value; if it's a Model, it's most likely not in DB"
                    )
                Select(selector.find_element(By.ID, bf.auto_id)).select_by_value(
                    f"{value}"
                )
            elif isinstance(bf.field.widget, forms.RadioSelect):
                value = bf.field.prepare_value(val_getter(data, bf.name))
                bw = next(
                    subwidget
                    for subwidget in bf.subwidgets
                    if subwidget.data["value"] == value
                )

                self.js_click(By.ID, bw.data["attrs"]["id"])
            # Provide other implementations here…
            # elif
            else:
                try:
                    elt: WebElement = selector.find_element(By.ID, bf.auto_id)
                    elt.clear()
                    elt.send_keys(val_getter(data, bf.name))
                except Exception:
                    self.fail(
                        f"Couldn't fill form field {bf.name} of type "
                        f"{type(bf.field.widget)} please provide an implementation"
                    )

    def js_click(self, by=By.ID, value: Optional[str] = None):
        """
        Clicking through Js instead of selenium to prevent
        'element is not clickable because another element obscures it' errors
        """
        for el in self.selenium.find_elements(by, value):
            self.selenium.execute_script("arguments[0].click();", el)

    @contextlib.contextmanager
    def details_opened(self, by=By.ID, value: Optional[str] = None):
        elt = self.selenium.find_element(by, value)
        try:
            self.selenium.execute_script(
                "arguments[0].setAttribute('open', 'open')", elt
            )
            yield
        finally:
            # If we moved away from the page (for instance when POSTing a form)
            # the element is stale so we ignore this exception
            with contextlib.suppress(StaleElementReferenceException):
                self.selenium.execute_script(
                    "arguments[0].removeAttribute('open')", elt
                )

    @contextlib.contextmanager
    def dropdown_opened(self, by=By.ID, value: Optional[str] = None):
        dropdown = self.selenium.find_element(by, value)
        button = dropdown.find_element(By.TAG_NAME, "button")
        button.click()
        try:
            yield dropdown
        finally:
            self.selenium.find_element(By.TAG_NAME, "body").click()

    @contextlib.contextmanager
    def implicitely_wait(self, time_to_wait: float, driver=None):
        """time_to_wait: time to wait in seconds"""
        driver = driver or self.selenium
        implicit_wait = driver.timeouts.implicit_wait
        driver.implicitly_wait(0.1)
        try:
            yield
        finally:
            driver.implicitly_wait(implicit_wait)

    def path_matches(
        self, viewname: str, *, kwargs: dict = None, query_params: dict = None
    ):
        kwargs = kwargs or {}
        query_part = urlencode(query_params or {}, quote_via=lambda s, _1, _2, _3: s)
        query_part = rf"\?{query_part}" if query_part else ""
        return url_matches(
            rf"http://localhost:\d+{reverse(viewname, kwargs=kwargs)}{query_part}"
        )

    def document_loaded(self) -> Callable[[WebDriver], bool]:
        def _predicate(driver: WebDriver) -> bool:
            return driver.execute_script("return document.readyState") == "complete"

        return _predicate

    def dsfr_ready(self):
        def _predicate(driver: WebDriver):
            return (
                driver.execute_script(
                    "return document.documentElement.dataset.appReady"
                )
                == "true"
            )

        return _predicate

    def assertElementNotFound(self, by=By.ID, value: Optional[str] = None):
        self.wait.until(self.document_loaded())
        with self.implicitely_wait(0.1):
            with self.assertRaises(
                NoSuchElementException, msg="Found element expected to be absent"
            ):
                self.selenium.find_element(by=by, value=value)

    def assertNormalizedStringEqual(self, first, second):
        """
        Compares to strings where all the newlines
        and multiple spaces are replaced with single space
        """
        return self.assertEqual(
            re.sub(r"\s+", " ", f"{first}", flags=re.M).strip(),
            re.sub(r"\s+", " ", f"{second}", flags=re.M).strip(),
        )

    # on exclue le warning aria-allowed-role sur les balises nav des skips-links car
    # role="navigation" explicitement demandé dans le composant skip link DSFR
    # Selon la doc dsfr, les composants fr-skiplinks, header, nav et footer doivent
    # déclarer les roles. axe-core considère que c'est redondant: on privilégie le dsfr
    def check_accessibility(
        self,
        page_name="page",
        strict=False,
        options={
            "exclude": [
                ["nav[aria-label='Accès rapide']"],
                ["header[role='banner']"],
                ["nav[role='navigation']"],
                ["footer[role='contentinfo']"],
            ]
        },
    ):
        """
        Check accessibility of the current page using axe-core

        Args:
            page_name: Name for the results file
            strict: If True, fail the test on violations
            options: Custom options for axe-core

        Returns:
            dict: axe-core results
        """
        if self.axe is None:
            self.axe = Axe(self.selenium)

        if not self._axe_injected:
            self.axe.inject()
            self._axe_injected = True

        try:
            results = self.axe.run(options=options)
        except Exception:
            # Re-inject if necessary (page/domain change)
            self.axe.inject()
            results = self.axe.run(options=options)

        # persist results
        # self.axe.write_results(results, f'{page_name}_a11y.json')

        # Handle violations
        violations_count = len(results["violations"])
        if violations_count > 0:
            violation_message = self.axe.report(results["violations"])

            if strict:
                self.assertEqual(violations_count, 0, violation_message)
            else:
                print(
                    f"\n{'=' * 100}\n",
                    f"\n⚠️  ACCESSIBILITY WARNING [{page_name}]:",
                    f"{violations_count} violation(s) detected",
                )
                print(f"{'=' * 100}\n")
                print(violation_message)

        return results

    def reset_axe_injection(self):
        """Reset injection flag (useful after navigating to a new domain)"""
        self._axe_injected = False
