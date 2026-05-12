from datetime import timedelta
from random import randint
from urllib.parse import urlencode

from django.test import tag
from django.urls import reverse
from django.utils import timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.models import Aidant, Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)

FIXED_PORT = randint(8081, 8179)


@tag("functional", "renew_mandat")
class RenewMandatTests(FunctionalTestCase):
    port = FIXED_PORT

    def setUp(self):
        self.otp = "123455"
        self.aidant: Aidant = AidantFactory(post__with_otp_device=["123456", self.otp])

    def test_renew_mandat(self):
        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(
            reverse("espace_aidant:renew_mandat", kwargs={"usager_id": self.usager.pk})
        )

        self.login_aidant(self.aidant)

        self.check_accessibility("espace_aidant:renew_mandat", strict=True)

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

        # Renew Mandat
        fc_button = self.selenium.find_element(By.ID, "submit_renew_button")
        fc_button.click()

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("Récapitulatif du mandat", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Fabrice Simpson ", recap_text)
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

        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 2)

    def test_renew_mandat_remote_mandat_with_legacy_consent(self):
        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(
            reverse("espace_aidant:renew_mandat", kwargs={"usager_id": self.usager.pk})
        )

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

        # Renew Mandat
        fc_button = self.selenium.find_element(By.ID, "submit_renew_button")
        fc_button.click()

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual("Récapitulatif du mandat à distance", recap_title)
        recap_text = self.selenium.find_element(By.ID, "recap-text").text
        self.assertIn("Fabrice Simpson ", recap_text)
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

        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 2)

    def test_sms_consent_is_not_available_from_renew_mandat_form(self):
        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(
            reverse("espace_aidant:renew_mandat", kwargs={"usager_id": self.usager.pk})
        )

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

    def path_matches(self, viewname: str, query_params: dict = None):
        query_part = urlencode(query_params or {}, quote_via=lambda s, _1, _2, _3: s)
        query_part = rf"\?{query_part}" if query_part else ""
        return url_matches(rf"http://localhost:\d+{reverse(viewname)}{query_part}")
