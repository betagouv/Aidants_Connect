import time
from datetime import timedelta

from django.conf import settings
from django.test import tag
from django.utils import timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_contains
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)

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
        self.aidant_2 = AidantFactory()
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
            mandat=mandat_aidant_1_jo_6,
            demarche="argent",
        )

        mandat_aidant_1_jo_12 = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )

        AutorisationFactory(
            mandat=mandat_aidant_1_jo_12,
            demarche="famille",
        )

        mandat_aidant_2_jo_12 = Mandat.objects.create(
            organisation=self.aidant_2.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=mandat_aidant_2_jo_12,
            demarche="logement",
        )

    def test_use_autorisation_with_preloging(self):
        # prelogin
        self.open_live_url("/espace-aidant/")
        self.login_aidant(self.aidant_1)

        url = f"/authorize/?{FC_URL_PARAMETERS}"
        self.open_live_url(url)

        self.use_a_autorisation()

    def test_use_autorisation_without_preloging(self):
        url = f"/authorize/?{FC_URL_PARAMETERS}"
        self.open_live_url(url)

        self.login_aidant(self.aidant_1)

        self.use_a_autorisation()

    def use_a_autorisation(self):
        # Select usager
        welcome_aidant = self.selenium.find_element(By.ID, "welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bienvenue Thierry !")

        self.selenium.find_element(By.CLASS_NAME, "ui-autocomplete-input")

        autocomplete = self.selenium.find_element(By.ID, "anonymous-filter-input")
        autocomplete.send_keys("Joséphine ST-PIERRE")
        usager = self.selenium.find_element(
            By.XPATH, f"//li[@data-value='{self.usager_josephine.id}']"
        )
        usager.click()

        button = self.selenium.find_element(By.ID, "submit-button")
        button.click()
        wait = WebDriverWait(self.selenium, 10)

        wait.until(url_contains("/select_demarche/"))

        # Select Démarche
        step2_title = self.selenium.find_element(By.CSS_SELECTOR, ".instructions").text
        self.assertIn("En sélectionnant une démarche", step2_title)
        demarches = self.selenium.find_elements(By.ID, "button-demarche")
        self.assertEqual(len(demarches), 2)
        last_demarche = demarches[-1]
        last_demarche.click()
        time.sleep(2)
        self.assertIn("fcp.integ01.dev-franceconnect.fr", self.selenium.current_url)
