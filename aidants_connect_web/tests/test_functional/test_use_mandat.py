from datetime import timedelta
import time

from django.conf import settings
from django.test import tag
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    AidantFactory,
    UsagerFactory,
    MandatFactory,
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
class UseNewMandat(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory()
        device = self.aidant.staticdevice_set.create(id=self.aidant.id)
        device.token_set.create(token="123456")
        self.aidant2 = AidantFactory(
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
        MandatFactory(
            aidant=self.aidant,
            usager=self.usager_josephine,
            demarche="argent",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        MandatFactory(
            aidant=self.aidant,
            usager=self.usager_josephine,
            demarche="famille",
            expiration_date=timezone.now() + timedelta(days=12),
        )
        MandatFactory(
            aidant=self.aidant2,
            usager=self.usager_josephine,
            demarche="logement",
            expiration_date=timezone.now() + timedelta(days=12),
        )

    def test_use_mandat_with_preloging(self):
        # prelogin
        self.open_live_url("/dashboard/")
        login_aidant(self)

        url = f"/authorize/?{FC_URL_PARAMETERS}"
        self.open_live_url(url)

        self.use_a_mandat()

    def test_use_mandat_without_preloging(self):
        url = f"/authorize/?{FC_URL_PARAMETERS}"
        self.open_live_url(url)

        login_aidant(self)

        self.use_a_mandat()

    def use_a_mandat(self):
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
