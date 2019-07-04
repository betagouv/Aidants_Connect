from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import User


class HomePage(StaticLiveServerTestCase):
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
            username="Thierry",
            email="thierry@thierry.com",
            password="motdepassedethierry",
            first_name="Thierry",
            last_name="Martin",
        )
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/dashboard/")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_login(self):
        login_field = self.selenium.find_element_by_id("id_username")
        login_field.send_keys("Thierry")
        password_field = self.selenium.find_element_by_id("id_password")
        password_field.send_keys("motdepassedethierry")
        submit_button = self.selenium.find_element_by_xpath('//input[@value="Login"]')
        submit_button.click()
        welcome_aidant = self.selenium.find_element_by_tag_name("h1").text

        # Create new user
        self.assertEqual(welcome_aidant, "Bienvenue sur votre espace aidant, Thierry !")
        add_user_button = self.selenium.find_element_by_id("add_user")
        add_user_button.click()
        procedure_section = self.selenium.find_element_by_id("select_procedure")
        procedure_title = procedure_section.find_element_by_tag_name("h2").text
        self.assertEqual(procedure_title, "Choisir la démarche")

        procedure_list = procedure_section.find_element_by_id("id_perimeter")
        procedures = procedure_list.find_elements_by_tag_name("label")

        print(procedures[0].__dict__)
        procedures[0].click()
        procedures[-1].click()
        self.assertEqual(len(procedures), 40)

        duration = procedure_section.find_element_by_id("id_duration")
        duration.send_keys("6")

        # FranceConnect
        fc_button = self.selenium.find_element_by_id("submit_button")
        # fc_button_link = fc_button.get_attribute("href")
        # self.assertIn("fc_authorize", fc_button_link)
        # fc_button.click()
        # fc_title = self.selenium.title
        # self.assertEqual("Connexion - choix du compte", fc_title)


class Error404Page(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/thiswontwork")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_404_page(self):
        H1 = self.selenium.find_element_by_tag_name("h1")
        self.assertEqual(H1.text, "Cette page n’existe pas (404)")
        link_to_home = self.selenium.find_element_by_id("to-home")
        self.assertEqual(link_to_home.text, "Retourner à l’accueil")
