from datetime import timedelta

from django.test import tag
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
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

        cls.usager = UsagerFactory(given_name="Joséphine")
        cls.usager2 = UsagerFactory(given_name="Corentin")
        cls.autorisation = AutorisationFactory(
            aidant=cls.aidant,
            usager=cls.usager,
            demarche=["social"],
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.autorisation2 = AutorisationFactory(
            aidant=cls.aidant,
            usager=cls.usager,
            demarche=["papiers"],
            expiration_date=timezone.now() + timedelta(days=1),
        )
        cls.autorisation3 = AutorisationFactory(
            aidant=cls.aidant,
            usager=cls.usager2,
            demarche=["famille"],
            expiration_date=timezone.now() + timedelta(days=365),
        )
        super().setUpClass()

    def test_grouped_autorisations(self):
        self.open_live_url("/dashboard/")

        # Login
        login_aidant(self)

        # Dashboard
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
