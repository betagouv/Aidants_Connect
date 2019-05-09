from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import User


class homePage(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_page_loads(self):
        H1 = self.selenium.find_element_by_tag_name("h1")
        self.assertEqual(H1.text, "Bienvenue sur Aidants Connect")


class LoginPage(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = User.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/authorize?state=34")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_page_loads(self):
        login_field = self.selenium.find_element_by_id("id_username")
        login_field.send_keys("Thierry")
        password_field = self.selenium.find_element_by_id("id_password")
        password_field.send_keys("motdepassedethierry")
        submit_button = self.selenium.find_element_by_xpath('//input[@value="Login"]')
        submit_button.click()
        welcome_aidant = self.selenium.find_element_by_id("welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bienvenue, aidant")
        # button = self.browser.find_element_by_id("submit")
