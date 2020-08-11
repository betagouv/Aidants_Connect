from datetime import timedelta

from django.test import tag
from django.utils import timezone

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    AutorisationFactory,
    UsagerFactory,
)
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional")
class CancelAutorisationTests(FunctionalTestCase):
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
        cls.usager_josephine = UsagerFactory(given_name="Joséphine")
        cls.mandat_thierry_josephine = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_thierry_josephine, demarche="argent",
        )
        AutorisationFactory(
            mandat=cls.mandat_thierry_josephine, demarche="famille",
        )

        cls.mandat_jacqueline_josephine = MandatFactory(
            organisation=cls.aidant_jacqueline.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=cls.mandat_jacqueline_josephine, demarche="logement",
        )
        super().setUpClass()

    def test_cancel_autorisation_of_active_mandat(self):
        self.open_live_url(f"/usagers/{self.usager_josephine.id}/")

        login_aidant(self)

        # See all mandats of usager page
        active_mandats_before = self.selenium.find_elements_by_id("active-mandat-panel")
        self.assertEqual(len(active_mandats_before), 1)
        active_mandats_autorisations_before = self.selenium.find_elements_by_id(
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

        # See again all mandats of usager page
        active_autorisations_after = self.selenium.find_elements_by_id(
            "active-mandat-panel"
        )
        self.assertEqual(len(active_autorisations_after), 1)
        active_mandats_autorisations_after = self.selenium.find_elements_by_id(
            "active-mandat-autorisation-row"
        )
        self.assertEqual(len(active_mandats_autorisations_after), 2)
        self.assertIn("Révoqué", active_mandats_autorisations_after[0].text)

        # Check Journal
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "cancel_autorisation")

        # Cancel second autorisation
        cancel_mandat_autorisation_button = active_mandats_autorisations_after[
            1
        ].find_element_by_tag_name("a")
        cancel_mandat_autorisation_button.click()

        # Confirm cancellation
        submit_button = self.selenium.find_elements_by_tag_name("input")[1]
        submit_button.click()

        # See again all mandats of usager page
        active_autorisations_after = self.selenium.find_elements_by_id(
            "active-mandat-panel"
        )
        self.assertEqual(len(active_autorisations_after), 0)
        inactive_autorisations_after = self.selenium.find_elements_by_id(
            "inactive-mandat-panel"
        )
        self.assertEqual(len(inactive_autorisations_after), 1)
        inactive_mandats_autorisations_after = self.selenium.find_elements_by_id(
            "inactive-mandat-autorisation-row"
        )
        self.assertEqual(len(inactive_mandats_autorisations_after), 2)
        self.assertIn("Révoqué", inactive_mandats_autorisations_after[0].text)
        self.assertIn("Révoqué", inactive_mandats_autorisations_after[1].text)
