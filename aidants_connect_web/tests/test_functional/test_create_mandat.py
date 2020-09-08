import time

from django.conf import settings
from django.test import tag

from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from aidants_connect_web.tests.test_functional.utilities import login_aidant


@tag("functional", "new_mandat")
class CreateNewMandatTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.port = settings.FC_AS_FS_TEST_PORT
        cls.aidant = AidantFactory()
        device = cls.aidant.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="123455")
        super().setUpClass()

    def test_create_new_mandat(self):
        self.open_live_url("/usagers/")

        login_aidant(self)

        welcome_aidant = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(welcome_aidant, "Vos usagers")

        usagers_before = self.selenium.find_elements_by_tag_name("tr")
        self.assertEqual(len(usagers_before), 0)

        # Create new mandat
        add_usager_button = self.selenium.find_element_by_id("add_usager")
        add_usager_button.click()

        demarches_section = self.selenium.find_element_by_id("demarches")
        demarche_title = demarches_section.find_element_by_tag_name("h2").text
        self.assertEqual(demarche_title, "Étape 1 : Sélectionnez la ou les démarche(s)")

        demarches_grid = self.selenium.find_element_by_id("demarches_list")
        demarches = demarches_grid.find_elements_by_tag_name("input")
        self.assertEqual(len(demarches), 10)

        demarches_section.find_element_by_id("argent").find_element_by_tag_name(
            "label"
        ).click()
        demarches_section.find_element_by_id("famille").find_element_by_tag_name(
            "label"
        ).click()

        duree_section = self.selenium.find_element_by_id("duree")
        duree_section.find_element_by_id("SHORT").find_element_by_tag_name(
            "label"
        ).click()

        # FranceConnect
        fc_button = self.selenium.find_element_by_id("submit_button")
        fc_button.click()
        fc_title = self.selenium.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        time.sleep(2)

        # Nouvelle mire dialog
        if len(self.selenium.find_elements_by_id("message-on-login")) > 0:
            temp_test_nouvelle_mire_masquer = self.selenium.find_element_by_id(
                "message-on-login-close"
            )
            temp_test_nouvelle_mire_masquer.click()

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
        submit_button = self.selenium.find_element_by_tag_name("button")
        submit_button.click()
        time.sleep(2)

        # Recap all the information for the Mandat
        recap_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(recap_title, "Récapitulatif du mandat")
        recap_text = self.selenium.find_element_by_id("recap_text").text
        self.assertIn("Angela Claire Louise DUBOIS ", recap_text)
        checkboxes = self.selenium.find_elements_by_tag_name("input")
        id_personal_data = checkboxes[1]
        self.assertEqual(id_personal_data.get_attribute("id"), "id_personal_data")
        id_personal_data.click()
        id_brief = checkboxes[2]
        self.assertEqual(id_brief.get_attribute("id"), "id_brief")
        id_brief.click()
        id_otp_token = checkboxes[3]
        self.assertEqual(id_otp_token.get_attribute("id"), "id_otp_token")
        id_otp_token.send_keys("123455")
        submit_button = checkboxes[-1]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()

        # Success page
        success_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(success_title, "Le mandat a été créé avec succès !")
        go_to_usager_button = self.selenium.find_element_by_class_name(
            "tiles"
        ).find_elements_by_tag_name("a")[1]
        go_to_usager_button.click()

        # See all mandats of usager page
        active_mandats_after = self.selenium.find_elements_by_tag_name("table")[
            0
        ].find_elements_by_css_selector("tbody tr")
        self.assertEqual(len(active_mandats_after), 2)
