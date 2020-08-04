from datetime import timedelta
import time

from django.conf import settings
from django.test import tag
from django.utils import timezone

from aidants_connect_web.models import Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


FC_URL_PARAMETERS = (
    f"state=34"
    f"&nonce=45"
    f"&response_type=code"
    f"&client_id={settings.FC_AS_FI_ID}"
    f"&redirect_uri={settings.FC_AS_FI_CALLBACK_URL}"
    f"&scope=openid profile email address phone birth"
    f"&acr_values=eidas1"
)


@tag("functional", "id_provider")
class UseAutorisationTests(FunctionalTestCase):
    def setUp(self):
        self.aidant_1 = AidantFactory()
        device = self.aidant_1.staticdevice_set.create(id=self.aidant_1.id)
        device.token_set.create(token="123456")
        self.aidant_2 = AidantFactory(
            username="jfremont@domain.user",
            email="jfremont@domain.user",
            password="motdepassedejacqueline",
            first_name="Jacqueline",
            last_name="Fremont",
        )
        self.usager_josephine = UsagerFactory(
            given_name="Joséphine", family_name="ST-PIERRE"
        )
        self.usager_anne = UsagerFactory(
            given_name="Anne Cécile Gertrude", family_name="EVALOUS"
        )

        mandat_aidant_1_jo_6 = MandatFactory(
            organisation=self.aidant_1.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=mandat_aidant_1_jo_6, demarche="argent",
        )

        mandat_aidant_1_jo_12 = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )

        AutorisationFactory(
            mandat=mandat_aidant_1_jo_12, demarche="famille",
        )

        mandat_aidant_2_jo_12 = Mandat.objects.create(
            organisation=self.aidant_2.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=mandat_aidant_2_jo_12, demarche="logement",
        )

    def test_use_autorisation_with_preloging(self):
        # prelogin
        self.open_live_url("/espace-aidant/")
        login_aidant(self)

        url = f"/authorize/?{FC_URL_PARAMETERS}"
        self.open_live_url(url)

        self.use_a_autorisation()

    def test_use_autorisation_without_preloging(self):
        url = f"/authorize/?{FC_URL_PARAMETERS}"
        self.open_live_url(url)

        login_aidant(self)

        self.use_a_autorisation()

    def use_a_autorisation(self):
        # Select usager
        welcome_aidant = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(
            welcome_aidant, "Bienvenue sur votre Espace Aidants Connect, Thierry"
        )
        usagers = self.selenium.find_elements_by_id("label-usager")
        self.assertEqual(len(usagers), 1)
        self.assertEqual(usagers[0].text, "Joséphine ST-PIERRE")
        usagers[0].click()

        # Select Démarche
        step2_title = self.selenium.find_element_by_id("instructions").text
        self.assertIn("En selectionnant une démarche", step2_title)
        demarches = self.selenium.find_elements_by_id("label_demarche")
        self.assertEqual(len(demarches), 2)
        last_demarche = demarches[-1]
        last_demarche.click()
        time.sleep(2)
        self.assertIn("fcp.integ01.dev-franceconnect.fr", self.selenium.current_url)
