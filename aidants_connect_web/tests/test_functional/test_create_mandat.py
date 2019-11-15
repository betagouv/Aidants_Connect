import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.test import tag
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional", "new_mandat")
class CreateNewMandat(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.port = settings.FC_AS_FS_TEST_PORT
        cls.aidant = Aidant.objects.create_user(
            username="Thierry",
            email="thierry@thierry.com",
            password="motdepassedethierry",
            first_name="Thierry",
            last_name="Martin",
        )
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/mandats/")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_create_new_mandat(self):
        login_aidant(self)

        welcome_aidant = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(welcome_aidant, "Vos mandats")

        self.assertEqual(len(self.selenium.find_elements_by_tag_name("tr")), 0)

        # Create new mandat
        add_usager_button = self.selenium.find_element_by_id("add_usager")
        add_usager_button.click()
        demarches_section = self.selenium.find_element_by_id("demarches")
        demarche_title = demarches_section.find_element_by_tag_name("h2").text
        self.assertEqual(demarche_title, "Étape 1 : Sélectionnez la ou les démarche(s)")

        demarches_section.find_element_by_id("argent").find_element_by_tag_name(
            "label"
        ).click()
        demarches_section.find_element_by_id("famille").find_element_by_tag_name(
            "label"
        ).click()

        demarches_grid = self.selenium.find_element_by_id("demarches_list")
        demarches = demarches_grid.find_elements_by_tag_name("input")
        self.assertEqual(len(demarches), 10)

        duree_section = self.selenium.find_element_by_id("duree")
        duree_section.find_element_by_id("long").find_element_by_tag_name(
            "label"
        ).click()

        # FranceConnect
        fc_button = self.selenium.find_element_by_id("submit_button")
        fc_button.click()
        fc_title = self.selenium.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        time.sleep(2)

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element_by_id(
            "fi-identity-provider-example"
        )
        demonstration_hex.click()
        time.sleep(2)

        # FC - Use the Mélaine_trois credentials
        demo_title = self.selenium.find_element_by_tag_name("h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        submit_button = self.selenium.find_elements_by_tag_name("input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # FC - Validate the information
        submit_button = self.selenium.find_element_by_tag_name("input")
        submit_button.click()
        time.sleep(2)

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(recap_title, "Récapitulatif")
        recap_text = self.selenium.find_element_by_id("recap_text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements_by_tag_name("input")
        id_personal_data = checkboxes[1]
        contact = self.selenium.find_element_by_tag_name("select")
        for option in contact.find_elements_by_tag_name("option"):
            if option.text == "SMS":
                option.click()
                break

        phone = self.selenium.find_element_by_name("contact_phone")
        phone.send_keys("0636656565")
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_brief = checkboxes[2]
        self.assertEqual(id_brief.get_attribute("id"), "id_brief")
        id_brief.click()
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        time.sleep(4)

        # back to dashboard
        self.assertEqual(welcome_aidant, "Vos mandats")
        self.selenium.find_element_by_id("view_mandats").click()

        # See all mandats page
        self.assertEqual(len(self.selenium.find_elements_by_tag_name("tr")), 3)
