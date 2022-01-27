from datetime import timedelta

from django.test import tag
from django.utils import timezone
from selenium.webdriver.common.by import By

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional")
class ViewAutorisationsTests(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory(email="thierry@thierry.com")
        device = self.aidant.staticdevice_set.create(id=self.aidant.id)
        device.token_set.create(token="123456")

        self.usager_alice = UsagerFactory(given_name="Alice", family_name="Lovelace")
        self.usager_josephine = UsagerFactory(
            given_name="Joséphine", family_name="Dupont"
        )
        self.usager_corentin = UsagerFactory(
            given_name="Corentin", family_name="Dupont", preferred_username="Astro"
        )

        self.mandat_aidant_alice_no_autorisation = MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_alice,
            expiration_date=timezone.now() + timedelta(days=5),
        )

        self.mandat_aidant_josephine_6 = MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=self.mandat_aidant_josephine_6,
            demarche="social",
        )

        self.mandat_aidant_josephine_1 = MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=1),
        )

        AutorisationFactory(
            mandat=self.mandat_aidant_josephine_1,
            demarche="papiers",
        )

        self.mandat_aidant_corentin_365 = MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_corentin,
            expiration_date=timezone.now() + timedelta(days=365),
        )
        AutorisationFactory(
            mandat=self.mandat_aidant_corentin_365,
            demarche="famille",
        )

    def test_grouped_autorisations(self):
        self.open_live_url("/espace-aidant/")

        # Login
        login_aidant(self)

        # Espace Aidant home
        self.selenium.find_element(By.ID, "view_mandats").click()

        results = []
        for el in self.selenium.find_elements(By.TAG_NAME, "table"):
            for tr in el.find_elements(By.CSS_SELECTOR, "tbody tr"):
                results.append(tr)

        # autorisation List
        self.assertEqual(len(results), 3)
