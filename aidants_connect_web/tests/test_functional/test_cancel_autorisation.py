from datetime import timedelta

from django.test import tag
from django.utils import timezone
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    AutorisationFactory,
    UsagerFactory,
)
from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional")
class CancelAutorisationTests(FunctionalTestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory(email="thierry@thierry.com")
        device = self.aidant_thierry.staticdevice_set.create(id=self.aidant_thierry.id)
        device.token_set.create(token="123456")
        self.aidant_jacqueline = AidantFactory()
        self.usager_josephine = UsagerFactory(given_name="Joséphine")
        self.mandat_thierry_josephine = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        self.money_authorization = AutorisationFactory(
            mandat=self.mandat_thierry_josephine,
            demarche="argent",
        )
        self.family_authorization = AutorisationFactory(
            mandat=self.mandat_thierry_josephine,
            demarche="famille",
        )

        self.mandat_jacqueline_josephine = MandatFactory(
            organisation=self.aidant_jacqueline.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=self.mandat_jacqueline_josephine,
            demarche="logement",
        )

    def test_cancel_autorisation_of_active_mandat(self):
        self.open_live_url(f"/usagers/{self.usager_josephine.id}/")

        login_aidant(self)

        # See all mandats of usager page
        active_mandats_before = self.selenium.find_elements_by_id("active-mandat-panel")
        self.assertEqual(len(active_mandats_before), 1)
        active_mandats_autorisations_before = self.selenium.find_elements_by_class_name(
            "active-mandat-autorisation-row"
        )
        self.assertEqual(len(active_mandats_autorisations_before), 2)

        # Cancel first autorisation
        cancel_mandat_autorisation_button = active_mandats_autorisations_before[
            0
        ].find_element_by_tag_name("a")
        cancel_mandat_autorisation_button.click()

        # Confirm cancellation
        submit_button = self.selenium.find_elements_by_tag_name("input")[1]
        submit_button.click()

        # Display attestation
        attestation_link = self.selenium.find_element_by_xpath(
            f'.//a[@href="/usagers/{self.usager_josephine.id}'
            f'/autorisations/{self.money_authorization.id}/cancel_attestation"]'
        )
        attestation_link.click()

        wait = WebDriverWait(self.selenium, 10)
        wait.until(lambda driver: len(driver.window_handles) == 2)
        self.selenium.switch_to.window(self.selenium.window_handles[1])

        recap_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(
            recap_title,
            "Révocation d'une autorisation via le service « Aidants Connect »",
        )

        self.selenium.close()
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        # See again all mandats of usager page
        user_link = self.selenium.find_element_by_xpath(
            f'.//a[@href="/usagers/{self.usager_josephine.id}/"]'
        )
        user_link.click()

        active_autorisations_after = self.selenium.find_elements_by_id(
            "active-mandat-panel"
        )
        self.assertEqual(len(active_autorisations_after), 1)

        active_mandats_autorisations_after = self.selenium.find_elements_by_class_name(
            "active-mandat-autorisation-row"
        )
        revoked_mandat_autorisation_after = self.selenium.find_element_by_id(
            f"active-mandat-autorisation-{self.money_authorization.demarche}"
        )

        self.assertEqual(len(active_mandats_autorisations_after), 2)
        self.assertIn("Révoqué", revoked_mandat_autorisation_after.text)

        auth_revocation_attestation_button = (
            self.selenium.find_elements_by_css_selector(
                ".button.auth-revocation-attestation"
            )
        )
        self.assertEqual(len(auth_revocation_attestation_button), 1)
        self.assertIn("Voir la révocation", auth_revocation_attestation_button[0].text)

        # Check Journal
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "cancel_autorisation")

        # Cancel second autorisation
        cancel_mandat_autorisation_button = self.selenium.find_element_by_id(
            f"active-mandat-autorisation-{self.family_authorization.demarche}"
        ).find_element_by_tag_name("a")
        cancel_mandat_autorisation_button.click()

        # Confirm cancellation
        submit_button = self.selenium.find_elements_by_tag_name("input")[1]
        submit_button.click()

        # See again all mandats of usager page
        user_link = self.selenium.find_element_by_xpath(
            f'.//a[@href="/usagers/{self.usager_josephine.id}/"]'
        )
        user_link.click()

        active_autorisations_after = self.selenium.find_elements_by_id(
            "active-mandat-panel"
        )
        self.assertEqual(len(active_autorisations_after), 0)
        inactive_autorisations_after = self.selenium.find_elements_by_id(
            "inactive-mandat-panel"
        )
        self.assertEqual(len(inactive_autorisations_after), 1)
        inactive_mandats_autorisations_after = (
            self.selenium.find_elements_by_class_name(
                "inactive-mandat-autorisation-row"
            )
        )
        self.assertEqual(len(inactive_mandats_autorisations_after), 2)
        self.assertIn("Révoqué", inactive_mandats_autorisations_after[0].text)
        self.assertIn("Révoqué", inactive_mandats_autorisations_after[1].text)
