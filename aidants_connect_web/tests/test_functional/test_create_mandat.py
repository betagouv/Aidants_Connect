from django.conf import settings
from django.test import Client, tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions

from aidants_connect_common.constants import AuthorizationDurations
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.models import Aidant, Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ConnectionFactory,
    UsagerFactory,
)


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
        self.usager = UsagerFactory(
            given_name="Angela Claire Louise",
            family_name="DUBOIS",
        )

    def _inject_session_cookie(
        self,
        is_remote=False,
        remote_constent_method=RemoteConsentMethodChoices.LEGACY.name,
    ):
        """Injecte le cookie de session configuré dans Selenium"""
        self.open_live_url("/")
        connection = ConnectionFactory(
            aidant=self.aidant,
            usager=self.usager,
            organisation=self.aidant.organisation,
            mandat_is_remote=is_remote,
            remote_constent_method=remote_constent_method,
            demarches=["argent", "famille"],
            duree_keyword=AuthorizationDurations.SHORT,
        )

        client = Client()
        client.force_login(self.aidant)

        session = client.session
        session["connection"] = connection.id
        session.save()
        self.session_key = session.session_key
        self.selenium.add_cookie(
            {
                "name": "sessionid",
                "value": self.session_key,
                "path": "/",
            }
        )

    def test_create_new_mandat(self):
        self.open_live_url(reverse("espace_aidant:new_mandat"))

        self.login_aidant(self.aidant)

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

        self._inject_session_cookie()
        self.open_live_url(reverse("espace_aidant:new_mandat_recap"))
        self.wait.until(self.path_matches("espace_aidant:new_mandat_recap"))

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("Récapitulatif du mandat", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")

        self.selenium.find_element(By.CSS_SELECTOR, "#id_personal_data ~ label").click()
        id_otp_token = checkboxes[-2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys(self.otp)
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(
            By.CSS_SELECTOR, ".attestation-content h1"
        ).text
        self.assertEqual(
            success_title,
            "Mandat pour réaliser des démarches en ligne\n"
            "avec le service « Aidants Connect »",
        )
        mandat_qs = Mandat.objects.filter(organisation=self.aidant.organisation)
        self.assertEqual(1, mandat_qs.count())
        self.assertEqual(2, mandat_qs[0].autorisations.count())

        self.open_live_url(reverse("espace_aidant:usagers"))

    def test_create_new_remote_mandat_with_legacy_consent(self):
        self.open_live_url(reverse("espace_aidant:new_mandat"))

        self.login_aidant(self.aidant)

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
            "Mandat court expire demain", short_duree_label.text.replace("\n", " ")
        )
        short_duree_label.click()

        # Enable remote signature
        self.selenium.find_element(By.CSS_SELECTOR, "#id_is_remote ~ label").click()
        self.assertEqual(
            "Mandat court à distance expire demain",
            self.selenium.find_element(
                By.CSS_SELECTOR, "#id_duree_short ~ label"
            ).text.replace("\n", " "),
        )

        remote_method = self.selenium.find_element(
            By.CSS_SELECTOR,
            'input[name="remote_constent_method"][type="hidden"]',
        )
        self.assertEqual(
            RemoteConsentMethodChoices.LEGACY.name,
            remote_method.get_attribute("value"),
        )
        self.assertFalse(
            self.selenium.find_elements(
                By.CSS_SELECTOR, 'input[id^="id_remote_constent_method"]'
            )
        )
        self.assertFalse(self.selenium.find_elements(By.ID, "id_user_phone"))
        self.assertFalse(
            self.selenium.find_elements(By.ID, "id_user_remote_contact_verified")
        )

        self._inject_session_cookie(is_remote=True)
        self.open_live_url(reverse("espace_aidant:new_mandat_recap"))
        self.wait.until(self.path_matches("espace_aidant:new_mandat_recap"))

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("Récapitulatif du mandat à distance", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements(By.TAG_NAME, "input")
        self.selenium.find_element(By.CSS_SELECTOR, "#id_personal_data ~ label").click()
        id_otp_token = checkboxes[-2]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys(self.otp)
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element(
            By.CSS_SELECTOR, ".attestation-content h1"
        ).text
        self.assertEqual(
            success_title,
            "Mandat pour réaliser des démarches en ligne\n"
            "avec le service « Aidants Connect »",
        )
        mandat_qs = Mandat.objects.filter(organisation=self.aidant.organisation)
        self.assertEqual(1, mandat_qs.count())
        self.assertEqual(2, mandat_qs[0].autorisations.count())

    def test_sms_consent_is_not_available_from_new_mandat_form(self):
        self.open_live_url(reverse("espace_aidant:new_mandat"))

        self.login_aidant(self.aidant)
        self.selenium.find_element(By.CSS_SELECTOR, "#id_is_remote ~ label").click()

        self.assertFalse(
            self.selenium.find_elements(By.ID, "id_remote_constent_method_sms")
        )
        self.assertFalse(self.selenium.find_elements(By.ID, "id_user_phone"))
        self.assertFalse(
            self.selenium.find_elements(By.ID, "id_user_remote_contact_verified")
        )
        self.assertEqual(
            RemoteConsentMethodChoices.LEGACY.name,
            self.selenium.find_element(
                By.CSS_SELECTOR,
                'input[name="remote_constent_method"][type="hidden"]',
            ).get_attribute("value"),
        )

    def test_bdf_warn_notification(self):
        self.open_live_url(reverse("espace_aidant:new_mandat"))

        self.login_aidant(self.aidant)

        demarches_section = self.selenium.find_element(
            By.CSS_SELECTOR, ".demarches-section"
        )

        demarches = demarches_section.find_elements(By.TAG_NAME, "input")
        self.assertEqual(len(demarches), 10)

        self.wait.until(
            expected_conditions.invisibility_of_element_located((By.ID, "bdf-warn-msg"))
        )

        self.assertFalse(
            self.selenium.find_element(By.ID, "bdf-warn-msg").is_displayed()
        )
        demarches_section.find_element(
            By.CSS_SELECTOR, "#id_demarche_argent ~ label"
        ).click()
        self.assertTrue(
            self.selenium.find_element(By.ID, "bdf-warn-msg").is_displayed()
        )

    def test_restrict_demarches(self):
        self.aidant.organisation.allowed_demarches = ["papiers", "famille", "social"]
        self.aidant.organisation.save()

        self.open_live_url(reverse("espace_aidant:new_mandat"))

        self.login_aidant(self.aidant)

        # Create new mandat
        demarches = self.selenium.find_elements(By.CSS_SELECTOR, '[id^="id_demarche_"]')
        self.assertEqual(
            ["papiers", "famille", "social"],
            [elt.get_attribute("value") for elt in demarches],
        )
