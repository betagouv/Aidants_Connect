from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import User
import time


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
        # FC only calls back on specific port
        cls.port = settings.FC_TEST_PORT
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

        procedures[0].click()
        procedures[-1].click()
        self.assertEqual(len(procedures), 40)

        duration = procedure_section.find_element_by_id("id_duration")
        duration.send_keys("6")

        # FranceConnect
        fc_button = self.selenium.find_element_by_id("submit_button")
        fc_button.click()
        fc_title = self.selenium.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        time.sleep(2)

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element_by_id("fi-identity-provider-example")
        demonstration_hex.click()
        time.sleep(2)

        # Use the Mélaine_trois credentials
        demo_title = self.selenium.find_element_by_tag_name("h3").text
        self.assertEqual(
            demo_title,
            "Fournisseur d'identité de démonstration"
        )
        submit_button = self.selenium.find_elements_by_tag_name("input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        time.sleep(2)
        recap_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(recap_title, "Récapitulatif")
        recap_text = self.selenium.find_elements_by_id("recap_text").text
        self.assertIn("Mélaine Évelyne TROIS", recap_text)





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
