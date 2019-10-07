from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import tag
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import Aidant, Usager, Mandat
from datetime import date
import time


@tag("functional", "id_provider")
class UseNewMandat(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant = Aidant.objects.create_user(
            username="Thierry",
            email="thierry@thierry.com",
            password="motdepassedethierry",
            first_name="Thierry",
            last_name="Martin",
        )
        Aidant.objects.create_user(
            username="jfremont@domain.user",
            email="jfremont@domain.user",
            password="motdepassedejacqueline",
            first_name="Jacqueline",
            last_name="Fremont",
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
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="argent",
            duree=6,
        )

        Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="famille",
            duree=12,
        )

        Mandat.objects.create(
            aidant=Aidant.objects.get(username="jfremont@domain.user"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche="logement",
            duree=12,
        )

        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_mandataires(self):
        browser = self.selenium

        browser.get(f"{self.live_server_url}/authorize/?state=34")

        # Login
        self.login_aidant()

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

    def login_aidant(self):
        login_field = self.selenium.find_element_by_id("id_email")
        login_field.send_keys("thierry@thierry.com")
        submit_button = self.selenium.find_element_by_xpath("//button")
        submit_button.click()
        email_sent_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(
            email_sent_title, "Un email vous a été envoyé pour vous connecter."
        )
        self.assertEqual(len(mail.outbox), 1)
        token_email = mail.outbox[0].body
        line_containing_magic_link = token_email.split("\n")[2]
        magic_link_https = line_containing_magic_link.split()[-1]
        magic_link_http = magic_link_https.replace("https", "http")
        self.selenium.get(magic_link_http)
