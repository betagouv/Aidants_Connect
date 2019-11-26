from datetime import date, timedelta
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.utils import timezone
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import Aidant, Usager, Mandat
from aidants_connect_web.tests.test_functional.utilities import login_aidant
from aidants_connect_web.tests.factories import UserFactory

import time


@tag("functional", "id_provider")
class UseNewMandat(StaticLiveServerTestCase):
    @classmethod
    def setUp(self):
        self.aidant = UserFactory()
        UserFactory(
            username="jfremont@domain.user",
            email="jfremont@domain.user",
            password="motdepassedejacqueline",
            first_name="Jacqueline",
            last_name="Fremont",
        )

        self.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate=date(1969, 12, 25),
            gender="female",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub",
            email="User@user.domain",
        )

        Usager.objects.create(
            given_name="Anne Cécile Gertrude",
            family_name="EVALOUS",
            preferred_username="Kasteign",
            birthdate=date(1945, 2, 14),
            gender="female",
            birthplace=27448,
            birthcountry=99100,
            sub="test_sub_2",
            email="akasteing@user.domain",
        )

        Mandat.objects.create(
            aidant=Aidant.objects.get(username="thierry@thierry.com"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="argent",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        Mandat.objects.create(
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
        self.selenium = WebDriver()
        self.selenium.implicitly_wait(3)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_use_mandat_with_preloging(self):
        self.use_a_mandat(prelogin=True)

    def test_use_mandat_without_preloging(self):
        self.use_a_mandat(prelogin=False)

    def use_a_mandat(self, prelogin: bool):
        browser = self.selenium
        if prelogin:
            browser.get(f"{self.live_server_url}/dashboard/")
            login_aidant(self)

        parameters = (
            f"state=34"
            f"&nonce=45"
            f"&response_type=code"
            f"&client_id={settings.FC_AS_FI_ID}"
            f"&redirect_uri={settings.FC_AS_FI_CALLBACK_URL}"
            f"&scope=openid profile email address phone birth"
            f"&acr_values=eidas1"
        )

        url = f"{self.live_server_url}/authorize/?{parameters}"
        browser.get(url)

        if not prelogin:
            login_aidant(self)

        # Select usager
        welcome_aidant = browser.find_element_by_tag_name("h1").text
        self.assertEqual(
            welcome_aidant, "Bienvenue sur votre Espace Aidants Connect, Thierry"
        )
        usagers = browser.find_elements_by_id("label-usager")
        self.assertEqual(len(usagers), 1)
        self.assertEqual(usagers[0].text, "ST-PIERRE Joséphine")
        usagers[0].click()

        # Select Démarche
        step2_title = browser.find_element_by_id("instructions").text
        self.assertIn("En selectionnant une démarche", step2_title)
        demarches = browser.find_elements_by_id("label_demarche")
        self.assertEqual(len(demarches), 2)
        last_demarche = demarches[-1]
        last_demarche.click()
        time.sleep(2)
        self.assertIn("fcp.integ01.dev-franceconnect.fr", browser.current_url)

        # Check user has been logged out by
        # checking if they are redirected to the login page
        self.aidant_is_disconnected(browser)

    def aidant_is_disconnected(self, browser):
        browser.get(f"{self.live_server_url}/authorize/?state=35")
        browser.find_element_by_id("id_email")
