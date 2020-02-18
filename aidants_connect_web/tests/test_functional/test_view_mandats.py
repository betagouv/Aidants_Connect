from datetime import date, timedelta

from django.test import tag
from django.utils import timezone

from aidants_connect_web.models import Aidant, Usager, Mandat
from aidants_connect_web.tests.factories import UserFactory
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional")
class ViewMandats(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = UserFactory()
        device = cls.user.staticdevice_set.create(id=cls.user.id)
        device.token_set.create(token="123456")

        cls.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate=date(1969, 12, 25),
            gender="female",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub",
            email="Aidant@user.domain",
        )
        cls.usager2 = Usager.objects.create(
            given_name="Corentin",
            family_name="DUPUIS",
            preferred_username="DUPUIS",
            birthdate=date(1983, 2, 3),
            gender="male",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub2",
            email="Aidant2@user.domain",
        )
        cls.mandat = Mandat.objects.create(
            aidant=Aidant.objects.get(username="thierry@thierry.com"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche=["social"],
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.mandat2 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="thierry@thierry.com"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche=["papiers"],
            expiration_date=timezone.now() + timedelta(days=1),
        )
        cls.mandat3 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="thierry@thierry.com"),
            usager=Usager.objects.get(sub="test_sub2"),
            demarche=["famille"],
            expiration_date=timezone.now() + timedelta(days=365),
        )
        super().setUpClass()

    def test_grouped_mandats(self):
        self.open_live_url("/dashboard/")

        # Login
        login_aidant(self)

        # Dashboard
        self.selenium.find_element_by_id("view_mandats").click()

        # Mandat List
        self.assertEqual(
            len(self.selenium.find_elements_by_class_name("fake-table-row")), 2
        )
