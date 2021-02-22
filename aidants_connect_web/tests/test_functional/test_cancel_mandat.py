from django.test import tag

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    AutorisationFactory,
)
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional", "cancel_mandat")
class CancelAutorisationTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant_thierry = AidantFactory()
        device = cls.aidant_thierry.staticdevice_set.create(id=cls.aidant_thierry.id)
        device.token_set.create(token="123456")

        cls.mandat = MandatFactory(organisation=cls.aidant_thierry.organisation)
        AutorisationFactory(
            mandat=cls.mandat,
            demarche="argent",
        )
        AutorisationFactory(
            mandat=cls.mandat,
            demarche="famille",
        )

        super().setUpClass()

    def test_cancel_autorisation_of_active_mandat(self):
        self.open_live_url(f"/usagers/{self.mandat.usager.id}/")

        login_aidant(self)

        # See all mandats of usager page
        active_mandats = self.selenium.find_elements_by_id("active-mandat-panel")
        self.assertEqual(len(active_mandats), 1)

        # Cancel mandat
        cancel_mandat_button = self.selenium.find_element_by_id("cancel_mandat")
        cancel_mandat_button.click()

        # Confirm cancellation
        submit_button = self.selenium.find_elements_by_tag_name("input")[1]
        submit_button.click()

        # See again all mandats of usager page

        inactive_mandats = self.selenium.find_elements_by_id("inactive-mandat-panel")
        self.assertEqual(len(inactive_mandats), 1)
        inactive_mandats_autorisations_after = self.selenium.find_elements_by_id(
            "inactive-mandat-autorisation-row"
        )
        self.assertEqual(len(inactive_mandats_autorisations_after), 2)
        self.assertIn("Révoqué", inactive_mandats_autorisations_after[0].text)

        # Check Journal
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "cancel_mandat")
