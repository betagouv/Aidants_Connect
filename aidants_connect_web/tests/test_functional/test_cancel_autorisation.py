from datetime import timedelta

from django.template.defaultfilters import date
from django.test import tag
from django.urls import reverse
from django.utils import timezone

from selenium.webdriver.common.by import By

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)


@tag("functional")
class CancelAutorisationTests(FunctionalTestCase):
    def setUp(self):
        self.selenium.implicitly_wait(10)
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

        self.login_aidant(self.aidant_thierry)

        # See all mandats of usager page
        active_mandats_before = self.selenium.find_elements(By.ID, "mandats-actifs")
        self.assertEqual(len(active_mandats_before), 1)
        active_mandats_autorisations_before = self.selenium.find_elements(
            By.CSS_SELECTOR, ".mandats-actifs .mandat-autorisation-row"
        )
        self.assertEqual(len(active_mandats_autorisations_before), 2)

        # Cancel first autorisation
        cancel_mandat_autorisation_button = active_mandats_autorisations_before[
            0
        ].find_element(By.TAG_NAME, "a")
        cancel_mandat_autorisation_button.click()

        # Confirm cancellation
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, "[type='submit']")
        submit_button.click()

        # Display attestation
        path = reverse(
            "autorisation_cancelation_attestation",
            kwargs={
                "usager_id": self.usager_josephine.id,
                "autorisation_id": self.money_authorization.id,
            },
        )
        self.check_accessibility("autorisation_cancelation_success", strict=False)

        self.selenium.find_element(By.XPATH, f'.//a[@href="{path}"]').click()

        self.wait.until(lambda driver: len(driver.window_handles) == 2)
        self.selenium.switch_to.window(self.selenium.window_handles[1])

        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(
            "révocation d'une autorisation via le service « aidants connect »",
            recap_title.casefold(),
        )

        self.selenium.close()
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        # See again all mandats of usager page
        self.open_live_url(
            reverse("usager_details", kwargs={"usager_id": self.usager_josephine.id})
        )
        self.check_accessibility("usager_details", strict=False)

        active_autorisations_after = self.selenium.find_elements(
            By.CLASS_NAME, "mandats-actifs"
        )
        self.assertEqual(len(active_autorisations_after), 1)

        active_mandats_autorisations_after = self.selenium.find_elements(
            By.CSS_SELECTOR, ".mandats-actifs .mandat-autorisation-row"
        )
        revoked_mandat_autorisation_after = self.selenium.find_element(
            By.ID,
            f"mandat-{self.mandat_thierry_josephine.pk}-"
            f"autorisation-{self.money_authorization.demarche}",
        )

        self.assertEqual(len(active_mandats_autorisations_after), 2)
        self.assertIn(
            date(timezone.now(), "d F Y"), revoked_mandat_autorisation_after.text
        )

        auth_revocation_attestation_button = self.selenium.find_elements(
            By.ID,
            f"mandat-{self.mandat_thierry_josephine.pk}-"
            f"auth-revocation-attestation-{self.money_authorization.demarche}",
        )
        self.assertEqual(len(auth_revocation_attestation_button), 1)
        self.assertIn("Voir la révocation", auth_revocation_attestation_button[0].text)

        # Check Journal
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "cancel_autorisation")

        # # Cancel second autorisation
        # cancel_mandat_autorisation_button = self.selenium.find_element(
        #     By.ID,
        #     f"mandat-{self.mandat_thierry_josephine.pk}-"
        #     f"auth-revocation-{self.family_authorization.demarche}",
        # )
        # cancel_mandat_autorisation_button.click()
        # self.wait.until(
        #     self.path_matches(
        #         "confirm_autorisation_cancelation",
        #         kwargs={
        #             "usager_id": self.mandat_thierry_josephine.pk,
        #             "autorisation_id": self.family_authorization.pk,
        #         },
        #     )
        # )
        #
        # # Confirm cancellation
        # submit_button = self.selenium.find_element(By.CSS_SELECTOR, "[type='submit']")
        # submit_button.click()
        #
        # self.wait.until(
        #     self.path_matches(
        #         "autorisation_cancelation_success",
        #         kwargs={
        #             "usager_id": self.mandat_thierry_josephine.pk,
        #             "autorisation_id": self.family_authorization.pk,
        #         },
        #     )
        # )
        #
        # self.open_live_url(
        #     reverse("usager_details", kwargs={"usager_id": self.usager_josephine.id})
        # )
        #
        # active_autorisations_after = self.selenium.find_elements(
        #     By.CSS_SELECTOR, ".mandats-actifs"
        # )
        # self.assertEqual(len(active_autorisations_after), 0)
        # inactive_autorisations_after = self.selenium.find_elements(
        #     By.CSS_SELECTOR, ".mandats-revoques"
        # )
        # self.assertEqual(len(inactive_autorisations_after), 1)
        # inactive_mandats_autorisations_after = self.selenium.find_elements(
        #     By.CSS_SELECTOR, ".mandats-revoques .mandat-autorisation-row"
        # )
        # self.assertEqual(len(inactive_mandats_autorisations_after), 2)
        # self.assertIn(
        #     date(timezone.now(), "d F Y"),
        #     inactive_mandats_autorisations_after[0].text
        # )
        # self.assertIn(
        #     date(timezone.now(), "d F Y"),
        #     inactive_mandats_autorisations_after[1].text
        # )
