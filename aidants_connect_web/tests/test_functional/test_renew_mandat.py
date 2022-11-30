from datetime import timedelta
from distutils.util import strtobool
from random import randint
from unittest import mock
from unittest.mock import Mock
from urllib.parse import urlencode

from django.conf import settings
from django.test import override_settings, tag
from django.urls import reverse
from django.utils import timezone

from phonenumbers import PhoneNumberFormat, format_number
from phonenumbers import parse as parse_number
from requests import post as requests_post
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.models import Journal, Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.tests.test_functional.utilities import login_aidant

UUID = "1f75d571-4127-445b-a141-ea837580da14"
FIXED_PORT = randint(8081, 8179)
DJANGO_SERVER_URL = f"http://localhost:{FIXED_PORT}"


@tag("functional", "renew_mandat")
class RenewMandatTests(FunctionalTestCase):
    port = FIXED_PORT

    def test_renew_mandat(self):
        self.aidant = AidantFactory(email="thierry@thierry.com")
        device = self.aidant.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="123455")

        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(f"/renew_mandat/{self.usager.pk}")

        login_aidant(self)

        demarches_section = self.selenium.find_element(By.ID, "demarches")
        demarche_title = demarches_section.find_element(By.TAG_NAME, "h2").text
        self.assertEqual(demarche_title, "Étape 1 : Sélectionnez la ou les démarche(s)")

        demarches_grid = self.selenium.find_element(By.ID, "demarches_list")
        demarches = demarches_grid.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element(By.ID, "argent").find_element(
            By.TAG_NAME, "label"
        ).click()
        demarches_section.find_element(By.ID, "famille").find_element(
            By.TAG_NAME, "label"
        ).click()

        duree_section = self.selenium.find_element(By.ID, "duree")
        duree_section.find_element(By.ID, "SHORT").find_element(
            By.TAG_NAME, "label"
        ).click()

        # Renew Mandat
        fc_button = self.selenium.find_element(By.ID, "submit_renew_button")
        fc_button.click()

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(recap_title, "Récapitulatif du mandat")
        recap_text = self.selenium.find_element(By.ID, "recap_text").text
        self.assertIn("Fabrice Simpson ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_otp_token = checkboxes[2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys("123455")
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(success_title, "Le mandat a été créé avec succès !")
        go_to_usager_button = self.selenium.find_element(
            By.CLASS_NAME, "tiles"
        ).find_elements(By.TAG_NAME, "a")[1]
        go_to_usager_button.click()

        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 2)

    def test_renew_mandat_remote_mandat_with_legacy_consent(self):
        wait = WebDriverWait(self.selenium, 10)

        self.aidant = AidantFactory(email="thierry@thierry.com")
        device = self.aidant.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="123455")

        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(f"/renew_mandat/{self.usager.pk}")

        login_aidant(self)

        demarches_section = self.selenium.find_element(By.ID, "demarches")
        demarche_title = demarches_section.find_element(By.TAG_NAME, "h2").text
        self.assertEqual(demarche_title, "Étape 1 : Sélectionnez la ou les démarche(s)")

        demarches_grid = self.selenium.find_element(By.ID, "demarches_list")
        demarches = demarches_grid.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element(By.ID, "argent").find_element(
            By.TAG_NAME, "label"
        ).click()
        demarches_section.find_element(By.ID, "famille").find_element(
            By.TAG_NAME, "label"
        ).click()

        duree_section = self.selenium.find_element(By.ID, "duree")
        duree_section.find_element(By.ID, "SHORT").find_element(
            By.TAG_NAME, "label"
        ).click()

        # Select remote method
        self.selenium.find_element(By.ID, "id_is_remote").click()

        # Check that I must fill a remote consent method
        # # wait for the execution of JS
        wait.until(self._element_is_required(By.ID, "id_remote_constent_method_legacy"))
        for elt in self.selenium.find_elements(
            By.CSS_SELECTOR, "#id_remote_constent_method input"
        ):
            self.assertTrue(elt.get_attribute("required"))

        # # Select legacy consent method
        text = RemoteConsentMethodChoices.LEGACY.label["label"]
        self.selenium.find_element(By.XPATH, f"//*[contains(text(), '{text}')]").click()

        # Renew Mandat
        fc_button = self.selenium.find_element(By.ID, "submit_renew_button")
        fc_button.click()

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(recap_title, "Récapitulatif du mandat")
        recap_text = self.selenium.find_element(By.ID, "recap_text").text
        self.assertIn("Fabrice Simpson ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_otp_token = checkboxes[2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys("123455")
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(success_title, "Le mandat a été créé avec succès !")
        go_to_usager_button = self.selenium.find_element(
            By.CLASS_NAME, "tiles"
        ).find_elements(By.TAG_NAME, "a")[1]
        go_to_usager_button.click()

        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 2)

    @override_settings(
        SMS_API_DISABLED=False,
        LM_SMS_SERVICE_USERNAME="username",
        LM_SMS_SERVICE_PASSWORD="password",
        LM_SMS_SERVICE_BASE_URL=DJANGO_SERVER_URL,
        LM_SMS_SERVICE_OAUTH2_ENDPOINT=reverse("test_sms_api_token"),
        LM_SMS_SERVICE_SND_SMS_ENDPOINT=reverse("test_sms_api_sms"),
    )
    @mock.patch("aidants_connect_web.views.renew_mandat.uuid4")
    def test_renew_mandat_remote_mandat_with_sms_consent(self, uuid4_mock: Mock):
        uuid4_mock.return_value = UUID
        wait = WebDriverWait(self.selenium, 10)

        self.aidant = AidantFactory(email="thierry@thierry.com")
        device = self.aidant.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="123455")

        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(f"/renew_mandat/{self.usager.pk}")

        login_aidant(self)

        demarches_section = self.selenium.find_element(By.ID, "demarches")
        demarche_title = demarches_section.find_element(By.TAG_NAME, "h2").text
        self.assertEqual(demarche_title, "Étape 1 : Sélectionnez la ou les démarche(s)")

        demarches_grid = self.selenium.find_element(By.ID, "demarches_list")
        demarches = demarches_grid.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element(By.ID, "argent").find_element(
            By.TAG_NAME, "label"
        ).click()
        demarches_section.find_element(By.ID, "famille").find_element(
            By.TAG_NAME, "label"
        ).click()

        duree_section = self.selenium.find_element(By.ID, "duree")
        duree_section.find_element(By.ID, "SHORT").find_element(
            By.TAG_NAME, "label"
        ).click()

        # Select remote method
        self.selenium.find_element(By.ID, "id_is_remote").click()

        # Check that I must fill a remote consent method
        # # wait for the execution of JS
        wait.until(self._element_is_required(By.ID, "id_remote_constent_method_legacy"))
        for elt in self.selenium.find_elements(
            By.CSS_SELECTOR, "#id_remote_constent_method input"
        ):
            self.assertTrue(elt.get_attribute("required"))

        # # Select SMS consent method
        text = RemoteConsentMethodChoices.SMS.label["label"]
        self.selenium.find_element(By.XPATH, f"//*[contains(text(), '{text}')]").click()
        wait.until(self._element_is_required(By.ID, "id_user_phone"))
        self.selenium.find_element(By.ID, "id_user_phone").send_keys("0 800 840 800")

        # Renew Mandat
        fc_button = self.selenium.find_element(By.ID, "submit_renew_button")
        fc_button.click()
        wait.until(self._path_matches("renew_mandat_waiting_room"))

        # Test that page blocks until user has consented
        self.selenium.refresh()
        wait.until(self._path_matches("renew_mandat_waiting_room"))

        # Simulate user content
        self._user_consents("0 800 840 800")
        wait.until(self._user_has_responded("0 800 840 800"))
        self.selenium.refresh()

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(recap_title, "Récapitulatif du mandat")
        recap_text = self.selenium.find_element(By.ID, "recap_text").text
        self.assertIn("Fabrice Simpson ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_otp_token = checkboxes[2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys("123455")
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(success_title, "Le mandat a été créé avec succès !")
        go_to_usager_button = self.selenium.find_element(
            By.CLASS_NAME, "tiles"
        ).find_elements(By.TAG_NAME, "a")[1]
        go_to_usager_button.click()

        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 2)

    def _element_is_required(self, by: By, value: str):
        def _predicate(driver: WebDriver):
            attr = driver.find_element(by, value).get_attribute("required")
            return strtobool(attr)

        return _predicate

    def _path_matches(self, route_name: str, query_params: dict = None):
        query_part = urlencode(query_params or {}, quote_via=lambda s, _1, _2, _3: s)
        query_part = rf"\?{query_part}" if query_part else ""
        return url_matches(rf"http://localhost:\d+{reverse(route_name)}{query_part}")

    def _user_responds(self, phone_number: str, text: str):
        number = parse_number(phone_number, settings.PHONENUMBER_DEFAULT_REGION)
        journal: Journal = Journal.objects.find_sms_consent_requests(
            number, UUID
        ).first()

        requests_post(
            f"{DJANGO_SERVER_URL}{reverse('sms_callback')}",
            json={
                "messageId": str(randint(10_000_000, 99_999_999)),
                "smsMTId": str(randint(10_000_000, 99_999_999)),
                "smsMTCorrelationId": journal.consent_request_id,
                "originatorAddress": format_number(number, PhoneNumberFormat.E164),
                "destinationAdress": str(randint(10_000, 99_999)),
                "timeStamp": timezone.now().isoformat(),
                "message": text,
                "userDataHeader": "",
                "mcc": "208",
                "mnc": "14",
            },
        )

    def _user_consents(self, phone_number: str):
        self._user_responds(phone_number, settings.SMS_RESPONSE_CONSENT)

    def _user_denies(self, phone_number: str):
        self._user_responds(phone_number, "Nope")

    def _user_has_responded(self, phone_number: str):
        def _predicate(driver):
            return Journal.objects.find_sms_user_consent_or_denial(
                parse_number(phone_number, settings.PHONENUMBER_DEFAULT_REGION), UUID
            ).exists()

        return _predicate
