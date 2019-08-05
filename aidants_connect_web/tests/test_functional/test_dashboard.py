from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import User, Usager, Mandat
from datetime import date


class CreateNewMandat(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.port = settings.FC_AS_FS_TEST_PORT
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
        cls.usager2 = Usager.objects.create(
            given_name="Corentin",
            family_name="DUPUIS",
            preferred_username="DUPUIS",
            birthdate=date(1983, 2, 3),
            gender="male",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub2",
            email="User2@user.domain",
        )
        cls.mandat = Mandat.objects.create(
            aidant=User.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            perimeter=["social"],
            duration=1,
        )
        cls.mandat2 = Mandat.objects.create(
            aidant=User.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            perimeter=["papiers"],
            duration=1,
        )
        cls.mandat3 = Mandat.objects.create(
            aidant=User.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub2"),
            perimeter=["famille"],
            duration=365,
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

        # login
        login_field = self.selenium.find_element_by_id("id_username")
        login_field.send_keys("Thierry")
        password_field = self.selenium.find_element_by_id("id_password")
        password_field.send_keys("motdepassedethierry")
        submit_button = self.selenium.find_element_by_xpath('//input[@value="Login"]')
        submit_button.click()

        # back to dashboard
        self.assertEqual(len(self.selenium.find_elements_by_class_name("usager")), 2)
        rows = self.selenium.find_elements_by_tag_name("tr")
        # The first row is the title row
        mandats = rows[1:]
        self.assertEqual(len(mandats), 3)
