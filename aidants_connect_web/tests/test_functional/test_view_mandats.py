from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail

from django.test import tag
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import Aidant, Usager, Mandat
from datetime import date


@tag("functional", "this")
class ViewMandats(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = Aidant.objects.create_user(
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
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche=["social"],
            duree=1,
        )
        cls.mandat2 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche=["papiers"],
            duree=1,
        )
        cls.mandat3 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub2"),
            demarche=["famille"],
            duree=365,
        )
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/dashboard/")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_grouped_mandats(self):
        self.selenium.get(f"{self.live_server_url}/dashboard/")

        # Login
        self.login_aidant()

        # Dashboard
        self.selenium.find_element_by_id("view_mandats").click()

        # Mandat List
        self.assertEqual(len(self.selenium.find_elements_by_class_name("usager")), 2)
        rows = self.selenium.find_elements_by_tag_name("tr")
        # The first row is the title row
        mandats = rows[1:]
        self.assertEqual(len(mandats), 3)

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
