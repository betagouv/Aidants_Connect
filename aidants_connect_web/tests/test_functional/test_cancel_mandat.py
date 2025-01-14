from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import AidantFactory, MandatFactory


@tag("functional", "cancel_mandat")
class CancelAutorisationTests(FunctionalTestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory(email="thierry@thierry.com")
        device = self.aidant_thierry.staticdevice_set.create(id=self.aidant_thierry.id)
        device.token_set.create(token="123456")

        self.mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            post__create_authorisations=["argent", "famille"],
        )

    def test_cancel_autorisation_of_active_mandat(self):
        self.open_live_url(f"/usagers/{self.mandat.usager.id}/")

        self.login_aidant(self.aidant_thierry)

        # See all mandats of usager page
        active_mandats = self.selenium.find_elements(By.ID, "mandats-actifs")
        self.assertEqual(len(active_mandats), 1)

        # Cancel mandat
        cancel_mandat_button = self.selenium.find_element(
            By.ID, f"cancel-mandat-{self.mandat.pk}"
        )
        cancel_mandat_button.click()

        remaining_autorisations = [
            it.text
            for it in self.selenium.find_elements(
                By.CSS_SELECTOR, ".remaining-autorisations strong"
            )
        ]
        self.assertEqual(
            remaining_autorisations,
            ["Argent - Impôts - Consommation", "Famille - Scolarité"],
        )

        # Confirm cancellation
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, "[type='submit']")
        submit_button.click()

        # Display attestation
        path = reverse(
            "mandat_cancellation_attestation", kwargs={"mandat_id": self.mandat.id}
        )
        self.selenium.find_element(By.XPATH, f'.//a[@href="{path}"]').click()

        self.wait.until(lambda driver: len(driver.window_handles) == 2)
        self.selenium.switch_to.window(self.selenium.window_handles[1])

        recap_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(
            "révocation d'un mandat via le service aidants connect",
            recap_title.casefold(),
        )

        self.selenium.close()
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        # See again all mandats of usager page

        self.open_live_url(
            reverse("usager_details", kwargs={"usager_id": self.mandat.usager.id})
        )

        inactive_mandats = self.selenium.find_elements(By.ID, "mandats-revoques")
        self.assertEqual(len(inactive_mandats), 1)
        inactive_mandats_autorisations_after = self.selenium.find_elements(
            By.CSS_SELECTOR, ".mandats-revoques .mandat-autorisation-row"
        )
        self.assertEqual(len(inactive_mandats_autorisations_after), 2)

        # Check Journal
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "cancel_mandat")
