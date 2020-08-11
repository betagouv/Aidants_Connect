from datetime import timedelta

from django.test import tag
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional")
class ViewAutorisationsTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant = AidantFactory()
        device = cls.aidant.staticdevice_set.create(id=cls.aidant.id)
        device.token_set.create(token="123456")

        cls.usager_josephine = UsagerFactory(given_name="Joséphine")
        cls.usager_corentin = UsagerFactory(given_name="Corentin")

        cls.mandat_aidant_josephine_6 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_josephine_6, demarche="social",
        )

        cls.mandat_aidant_josephine_1 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=1),
        )

        AutorisationFactory(
            mandat=cls.mandat_aidant_josephine_1, demarche="papiers",
        )

        cls.mandat_aidant_corentin_365 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_corentin,
            expiration_date=timezone.now() + timedelta(days=365),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_corentin_365, demarche="famille",
        )

        super().setUpClass()

    def test_grouped_autorisations(self):
        self.open_live_url("/espace-aidant/")

        # Login
        login_aidant(self)

        # Espace Aidant home
        self.selenium.find_element_by_id("view_mandats").click()

        # autorisation List
        self.assertEqual(
            len(
                self.selenium.find_element_by_tag_name(
                    "table"
                ).find_elements_by_css_selector("tbody tr")
            ),
            2,
        )
