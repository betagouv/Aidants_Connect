import time
from datetime import timedelta
from selenium.webdriver.firefox.webdriver import WebDriver

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.utils import timezone

from aidants_connect_web.tests.test_functional.utilities import login_aidant
from aidants_connect_web.tests.factories import UserFactory, UsagerFactory
from aidants_connect_web.models import Aidant, Usager, Mandat


@tag("functional")
class CancelMandat(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant = UserFactory()
        UserFactory(
            username="jfremont@domain.user",
            email="jfremont@domain.user",
            password="motdepassedejacqueline",
            first_name="Jacqueline",
            last_name="Fremont",
        )
        cls.usager = UsagerFactory(given_name="Joséphine", sub="test_sub",)
        cls.mandat_1 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="thierry@thierry.com"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="argent",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.mandat_2 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="thierry@thierry.com"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="famille",
            expiration_date=timezone.now() + timedelta(days=12),
        )
        Mandat.objects.create(
            aidant=Aidant.objects.get(username="jfremont@domain.user"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="logement",
            expiration_date=timezone.now() + timedelta(days=12),
        )

        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(3)
        cls.selenium.get(f"{cls.live_server_url}/usagers/{cls.usager.id}/")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_cancel_mandat(self):
        login_aidant(self)

        # See all mandats of usager page
        self.assertEqual(
            len(self.selenium.find_elements_by_class_name("fake-table-row")), 2
        )

        # Click on cancel mandat button
        cancel_mandat_button = self.selenium.find_elements_by_class_name(
            "fake-table-row"
        )[0].find_element_by_tag_name("a")
        cancel_mandat_button.click()
        time.sleep(1)

        # Click on confirm cancellation
        submit_button = self.selenium.find_elements_by_tag_name("input")[1]
        submit_button.click()
        time.sleep(1)

        # See all mandats of usager page
        self.assertEqual(
            len(self.selenium.find_elements_by_class_name("fake-table-row")), 1
        )
