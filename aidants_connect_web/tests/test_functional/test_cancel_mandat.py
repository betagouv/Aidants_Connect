from datetime import timedelta

from django.test import tag
from django.utils import timezone

from aidants_connect_web.models import Journal, Mandat
from aidants_connect_web.tests.factories import AidantFactory, UsagerFactory
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional")
class CancelMandat(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant_thierry = AidantFactory()
        device = cls.aidant_thierry.staticdevice_set.create(id=cls.aidant_thierry.id)
        device.token_set.create(token="123456")

        cls.aidant_jacqueline = AidantFactory(
            username="jfremont@domain.user",
            email="jfremont@domain.user",
            password="motdepassedejacqueline",
            first_name="Jacqueline",
            last_name="Fremont",
        )
        cls.usager_josephine = UsagerFactory(given_name="Joséphine", sub="test_sub",)
        cls.mandat_1 = Mandat.objects.create(
            aidant=cls.aidant_thierry,
            usager=cls.usager_josephine,
            demarche="argent",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.mandat_2 = Mandat.objects.create(
            aidant=cls.aidant_thierry,
            usager=cls.usager_josephine,
            demarche="famille",
            expiration_date=timezone.now() + timedelta(days=12),
        )
        Mandat.objects.create(
            aidant=cls.aidant_jacqueline,
            usager=cls.usager_josephine,
            demarche="logement",
            expiration_date=timezone.now() + timedelta(days=12),
        )

        super().setUpClass()

    def test_cancel_mandat(self):
        self.open_live_url(f"/usagers/{self.usager_josephine.id}/")

        login_aidant(self)

        # See all mandats of usager page
        active_mandats_before = self.selenium.find_elements_by_class_name(
            "fake-table-row"
        )
        self.assertEqual(len(active_mandats_before), 2)

        # Click on cancel mandat button
        cancel_mandat_button = active_mandats_before[0].find_element_by_tag_name("a")
        cancel_mandat_button.click()

        # Click on confirm cancellation
        submit_button = self.selenium.find_elements_by_tag_name("input")[1]
        submit_button.click()

        # See all mandats of usager page
        active_mandats_after = self.selenium.find_elements_by_class_name(
            "fake-table-row"
        )
        self.assertEqual(len(active_mandats_after), 1)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "cancel_mandat")
