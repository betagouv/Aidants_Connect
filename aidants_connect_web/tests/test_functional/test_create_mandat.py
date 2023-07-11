from distutils.util import strtobool
from random import randint
from unittest import mock
from unittest.mock import Mock

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

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.models import Aidant, Journal, Mandat
from aidants_connect_web.tests.factories import AidantFactory

UUID = "1f75d571-4127-445b-a141-ea837580da14"


@tag("functional", "new_mandat")
class CreateNewMandatTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.port = settings.FC_AS_FS_TEST_PORT
        super().setUpClass()

    def setUp(self):
        self.otp = "123455"
        self.aidant: Aidant = AidantFactory(post__with_otp_device=["123456", self.otp])

    def test_create_new_mandat(self):
        self.open_live_url("/usagers/")

        self.login_aidant(self.aidant)

        welcome_aidant = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(welcome_aidant, "Vos usagères et usagers")

        usagers_before = self.selenium.find_elements(By.CSS_SELECTOR, ".tiles *")
        self.assertEqual(1, len(usagers_before))
        self.assertEqual(
            "Il n'y a encore personne avec qui vous avez un mandat.",
            usagers_before[0].text.strip(),
        )

        # Create new mandat
        self.selenium.find_element(By.ID, "add_usager").click()
        self.wait.until(self.path_matches("new_mandat"))

        demarches_section = self.selenium.find_element(
            By.CSS_SELECTOR, ".demarches-section"
        )

        demarches = demarches_section.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_argent ~ label"
        ).click()
        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_famille ~ label"
        ).click()

        self.selenium.find_element(By.CSS_SELECTOR, "#id_duree_short ~ label").click()

        # FranceConnect
        fc_button = self.selenium.find_element(By.ID, "submit_button")
        fc_button.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/api/v1/authorize.+"))
        fc_title = self.selenium.title
        self.assertEqual("Connexion - choix du compte", fc_title)

        # Nouvelle mire dialog
        if len(self.selenium.find_elements(By.ID, "message-on-login")) > 0:
            temp_test_nouvelle_mire_masquer = self.selenium.find_element(
                By.ID, "message-on-login-close"
            )
            temp_test_nouvelle_mire_masquer.click()

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element(
            By.ID, "fi-identity-provider-example"
        )
        demonstration_hex.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/interaction/.+"))

        # FC - Use the Mélaine_trois credentials
        demo_title = self.selenium.find_element(By.TAG_NAME, "h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        submit_button = self.selenium.find_elements(By.TAG_NAME, "input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/api/v1/authorize.+"))

        # FC - Validate the information
        submit_button = self.selenium.find_element(By.TAG_NAME, "button")
        submit_button.click()
        self.wait.until(
            self.path_matches("new_mandat_recap", query_params={"state": ".+"})
        )

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("RÉCAPITULATIF DU MANDAT", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_otp_token = checkboxes[2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys(self.otp)
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(
            success_title,
            "Mandat pour réaliser des démarches "
            "en ligne avec le service « Aidants Connect »",
        )
        mandat_qs = Mandat.objects.filter(organisation=self.aidant.organisation)
        self.assertEqual(1, mandat_qs.count())
        self.assertEqual(2, mandat_qs[0].autorisations.count())

    def test_create_new_remote_mandat_with_legacy_consent(self):
        self.open_live_url("/usagers/")

        self.login_aidant(self.aidant)

        welcome_aidant = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(welcome_aidant, "Vos usagères et usagers")

        usagers_before = self.selenium.find_elements(By.CSS_SELECTOR, ".tiles *")
        self.assertEqual(1, len(usagers_before))
        self.assertEqual(
            "Il n'y a encore personne avec qui vous avez un mandat.",
            usagers_before[0].text.strip(),
        )

        # Create new mandat
        self.selenium.find_element(By.ID, "add_usager").click()
        self.wait.until(self.path_matches("new_mandat"))

        demarches_section = self.selenium.find_element(
            By.CSS_SELECTOR, ".demarches-section"
        )
        demarches = demarches_section.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_argent ~ label"
        ).click()
        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_famille ~ label"
        ).click()

        short_duree_label = self.selenium.find_element(
            By.CSS_SELECTOR, "#id_duree_short ~ label"
        )
        self.assertEqual(
            "MANDAT COURT (expire demain)", short_duree_label.text.replace("\n", " ")
        )
        short_duree_label.click()

        # Select remote method
        self.selenium.find_element(By.ID, "id_is_remote").click()
        self.assertEqual(
            "MANDAT COURT À DISTANCE (expire demain)",
            self.selenium.find_element(
                By.CSS_SELECTOR, "#id_duree_short ~ label"
            ).text.replace("\n", " "),
        )

        # Check that I must fill a remote consent method
        # # wait for the execution of JS
        self.wait.until(
            self._element_is_required(By.ID, "id_remote_constent_method_legacy")
        )
        elts = self.selenium.find_elements(
            By.CSS_SELECTOR, 'input[id^="id_remote_constent_method"]'
        )
        self.assertEqual(2, len(elts))
        [self.assertTrue(elt.get_attribute("required")) for elt in elts]

        # # Select legacy consent method
        text = RemoteConsentMethodChoices.LEGACY.label["label"]
        self.selenium.find_element(By.XPATH, f"//*[contains(text(), '{text}')]").click()

        # FranceConnect
        fc_button = self.selenium.find_element(By.ID, "submit_button")
        fc_button.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/api/v1/authorize.+"))

        # Nouvelle mire dialog
        if len(self.selenium.find_elements(By.ID, "message-on-login")) > 0:
            temp_test_nouvelle_mire_masquer = self.selenium.find_element(
                By.ID, "message-on-login-close"
            )
            temp_test_nouvelle_mire_masquer.click()

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element(
            By.ID, "fi-identity-provider-example"
        )
        demonstration_hex.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/interaction/.+"))

        # FC - Use the Mélaine_trois credentials
        demo_title = self.selenium.find_element(By.TAG_NAME, "h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        submit_button = self.selenium.find_elements(By.TAG_NAME, "input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/api/v1/authorize.+"))

        # FC - Validate the information
        submit_button = self.selenium.find_element(By.TAG_NAME, "button")
        submit_button.click()
        self.wait.until(
            self.path_matches("new_mandat_recap", query_params={"state": ".+"})
        )

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("RÉCAPITULATIF DU MANDAT À DISTANCE", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_otp_token = checkboxes[2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys(self.otp)
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(
            success_title,
            "Mandat pour réaliser des démarches "
            "en ligne avec le service « Aidants Connect »",
        )
        mandat_qs = Mandat.objects.filter(organisation=self.aidant.organisation)
        self.assertEqual(1, mandat_qs.count())
        self.assertEqual(2, mandat_qs[0].autorisations.count())

    @override_settings(
        SMS_API_DISABLED=False,
        LM_SMS_SERVICE_USERNAME="username",
        LM_SMS_SERVICE_PASSWORD="password",
        LM_SMS_SERVICE_BASE_URL=f"http://localhost:{settings.FC_AS_FS_TEST_PORT}",
        LM_SMS_SERVICE_OAUTH2_ENDPOINT=reverse("test_sms_api_token"),
        LM_SMS_SERVICE_SND_SMS_ENDPOINT=reverse("test_sms_api_sms"),
    )
    @mock.patch("aidants_connect_web.views.mandat.uuid4")
    def test_create_new_remote_mandat_with_sms_consent(self, uuid4_mock: Mock):
        uuid4_mock.return_value = UUID

        self.open_live_url("/usagers/")

        self.login_aidant(self.aidant)

        welcome_aidant = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(welcome_aidant, "Vos usagères et usagers")

        usagers_before = self.selenium.find_elements(By.CSS_SELECTOR, ".tiles *")
        self.assertEqual(1, len(usagers_before))
        self.assertEqual(
            "Il n'y a encore personne avec qui vous avez un mandat.",
            usagers_before[0].text.strip(),
        )

        # Create new mandat
        self.selenium.find_element(By.ID, "add_usager").click()
        self.wait.until(self.path_matches("new_mandat"))

        demarches_section = self.selenium.find_element(
            By.CSS_SELECTOR, ".demarches-section"
        )
        demarches = demarches_section.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_argent ~ label"
        ).click()
        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_famille ~ label"
        ).click()

        short_duree_label = self.selenium.find_element(
            By.CSS_SELECTOR, "#id_duree_short ~ label"
        )
        short_duree_label.click()
        self.assertEqual(
            "MANDAT COURT (expire demain)", short_duree_label.text.replace("\n", " ")
        )

        # Select remote method
        self.selenium.find_element(By.ID, "id_is_remote").click()
        self.assertEqual(
            "MANDAT COURT À DISTANCE (expire demain)",
            self.selenium.find_element(
                By.CSS_SELECTOR, "#id_duree_short ~ label"
            ).text.replace("\n", " "),
        )

        # Check that I must fill a remote consent method
        # # wait for the execution of JS
        self.wait.until(
            self._element_is_required(By.ID, "id_remote_constent_method_sms")
        )
        elts = self.selenium.find_elements(
            By.CSS_SELECTOR, 'input[id^="id_remote_constent_method"]'
        )
        self.assertEqual(2, len(elts))
        [self.assertTrue(elt.get_attribute("required")) for elt in elts]

        # # Select SMS consent method
        text = RemoteConsentMethodChoices.SMS.label["label"]
        self.selenium.find_element(By.XPATH, f"//*[contains(text(), '{text}')]").click()
        self.wait.until(self._element_is_required(By.ID, "id_user_phone"))
        self.wait.until(
            self._element_is_required(By.ID, "id_user_remote_contact_verified")
        )
        self.selenium.find_element(By.ID, "id_user_phone").send_keys("0 800 840 800")
        self.selenium.find_element(By.ID, "id_user_remote_contact_verified").click()

        # # Send recap mandate and go to second step
        self.selenium.find_element(By.ID, "submit_button").click()
        self.wait.until(self.path_matches("new_mandat_remote_second_step"))

        # # Send user consent request
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait.until(self.path_matches("new_mandat_waiting_room"))

        # # Test the message is correctly logged
        consent_request_log: Journal = Journal.objects.find_sms_consent_requests(
            parse_number("0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION), UUID
        )[0]

        self.assertIn(
            "Aidant Connect, bonjour",
            consent_request_log.additional_information,
        )

        # # Test that page blocks until user has consented
        self.selenium.refresh()
        self.wait.until(self.path_matches("new_mandat_waiting_room"))

        # Try to force creation of mandate; should be redirected to waiting room
        self.open_live_url(reverse("new_mandat_recap"))
        self.wait.until(self.path_matches("new_mandat_waiting_room"))

        # Simulate user content
        self._user_consents("0 800 840 800")
        self.wait.until(self._user_has_responded("0 800 840 800"))
        # # Test user consent is correctly logged
        user_consent_log: Journal = Journal.objects.find_sms_user_consent(
            parse_number("0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION), UUID
        )[0]
        self.assertEqual("message=Oui", user_consent_log.additional_information)

        # Testing JS script
        # Change poll time for immediate execution
        self.selenium.execute_script(
            """
            document.querySelector(
                "[data-controller='remote-consent-waiting-room']"
            ).setAttribute(
                "data-remote-content-waiting-room-poll-timeout-value", "1"
            )
        """
        )
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/api/v1/authorize.+"))

        # Nouvelle mire dialog
        if len(self.selenium.find_elements(By.ID, "message-on-login")) > 0:
            temp_test_nouvelle_mire_masquer = self.selenium.find_element(
                By.ID, "message-on-login-close"
            )
            temp_test_nouvelle_mire_masquer.click()

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element(
            By.ID, "fi-identity-provider-example"
        )
        demonstration_hex.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/interaction/.+"))

        # FC - Use the Mélaine_trois credentials
        demo_title = self.selenium.find_element(By.TAG_NAME, "h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        submit_button = self.selenium.find_elements(By.TAG_NAME, "input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        self.wait.until(url_matches(r"https://.+franceconnect\.fr/api/v1/authorize.+"))

        # FC - Validate the information
        submit_button = self.selenium.find_element(By.TAG_NAME, "button")
        submit_button.click()
        self.wait.until(
            self.path_matches("new_mandat_recap", query_params={"state": ".+"})
        )

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("RÉCAPITULATIF DU MANDAT À DISTANCE", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_otp_token = checkboxes[2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys(self.otp)
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(
            success_title,
            "Mandat pour réaliser des démarches en "
            "ligne avec le service « Aidants Connect »",
        )
        mandat_qs = Mandat.objects.filter(organisation=self.aidant.organisation)
        self.assertEqual(1, mandat_qs.count())
        self.assertEqual(2, mandat_qs[0].autorisations.count())

    def _element_is_required(self, by: By, value: str):
        def _predicate(driver: WebDriver):
            attr = driver.find_element(by, value).get_attribute("required")
            return strtobool(attr)

        return _predicate

    def _user_responds(self, phone_number: str, text: str):
        number = parse_number(phone_number, settings.PHONENUMBER_DEFAULT_REGION)
        journal: Journal = Journal.objects.find_sms_consent_requests(
            number, UUID
        ).first()

        requests_post(
            f"http://localhost:{settings.FC_AS_FS_TEST_PORT}{reverse('sms_callback')}",
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
        self._user_responds(phone_number, "Oui")

    def _user_denies(self, phone_number: str):
        self._user_responds(phone_number, "Nope")

    def _user_has_responded(self, phone_number: str):
        def _predicate(driver):
            return Journal.objects.find_sms_user_consent_or_denial(
                parse_number(phone_number, settings.PHONENUMBER_DEFAULT_REGION), UUID
            ).exists()

        return _predicate
