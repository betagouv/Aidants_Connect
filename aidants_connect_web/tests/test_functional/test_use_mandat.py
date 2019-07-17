from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import User, Usager, Mandat
from datetime import date
import time


class CreateNewMandat(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.user = User.objects.create_user(
            username="Thierry",
            email="thierry@thierry.com",
            password="motdepassedethierry",
            first_name="Thierry",
            last_name="Martin",
        )
        cls.usager = Usager.objects.create(
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
        cls.mandat = Mandat.objects.create(
            aidant=User.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            perimeter=["Revenus"],
            duration=6,
        )
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_mandataires(self):
        self.selenium.get(f"{self.live_server_url}/authorize/?state=34")
        browser = self.selenium
        login_field = browser.find_element_by_id("id_username")
        login_field.send_keys("Thierry")
        password_field = browser.find_element_by_id("id_password")
        password_field.send_keys("motdepassedethierry")
        submit_button = browser.find_element_by_xpath('//input[@value="Login"]')
        submit_button.click()
        welcome_aidant = browser.find_element_by_tag_name("h2").text
        self.assertEqual(welcome_aidant, "Bienvenue, Thierry")
        usager = browser.find_element_by_id("submit")
        self.assertEqual(usager.text, "Joséphine ST-PIERRE")
        usager.click()
        step2_title = browser.find_element_by_id("instructions").text
        self.assertEqual(step2_title, "Sélectionnez une démarche")
        demarche = browser.find_elements_by_id("submit")[-1]
        self.assertIn(demarche.text, "Revenus")
        demarche.click()
        time.sleep(2)
        self.assertIn("fcp.integ01.dev-franceconnect.fr", browser.current_url)
