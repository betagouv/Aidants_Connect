from selenium import webdriver
import unittest
import time


class NewVisitorConnection(unittest.TestCase):

    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.get('http://localhost:1337')

    def tearDown(self):
        self.browser.quit()

    def test_page_loads(self):
        welcome_aidant = self.browser.find_element_by_id("welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bienvenue, aidant")

    def test_fc_button(self):
        # Click on the FranceConnect button
        fc_button = self.browser.find_element_by_id("bouton_fc")
        fc_button_link = fc_button.get_attribute("href")
        self.assertIn("fc_authorize", fc_button_link)
        fc_button.click()
        time.sleep(2)

        # Click on the 'Démonstration' identity provider
        fc_title = self.browser.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        demonstration_hex = \
            self.browser.find_elements_by_class_name("hexLink")[1]
        demonstration_hex.click()
        time.sleep(2)

        # Use the Aidant credentials (Mélaine)
        demo_title = self.browser.find_element_by_tag_name("h3").text
        self.assertEqual(
            demo_title,
            "Fournisseur d'identité de démonstration"
            )
        submit_button = self.browser.find_elements_by_tag_name("input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        time.sleep(2)
        welcome_aidant = self.browser.find_element_by_id("welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bonjour Mélaine Évelyne")

        # Click on the FranceConnect button for usager
        fc_button = self.browser.find_element_by_id("bouton_fc")
        fc_button_link = fc_button.get_attribute("href")
        self.assertIn("fc_authorize", fc_button_link)
        fc_button.click()
        time.sleep(2)

        # Click on the 'Démonstration' identity provider
        fc_title = self.browser.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        demonstration_hex = \
            self.browser.find_elements_by_class_name("hexLink")[1]
        demonstration_hex.click()
        time.sleep(2)

        # Use the Usager credentials (mercier_eric@mail.com)

        # demo_title = self.browser.find_element_by_tag_name("h3").text
        # self.assertEqual(
        #     demo_title,
        #     "Fournisseur d'identité de démonstration"
        # )
        # email_input = self.browser.find_elements_by_tag_name("input")[0]
        # password_input = self.browser.find_elements_by_tag_name("input")[1]
        # # TODO Input mercier_eric@mail.com
        # # todo Input password
        # submit_button = self.browser.find_elements_by_tag_name("input")[2]
        # self.assertEqual(submit_button.get_attribute("type"), "submit")
        # submit_button.click()
        # time.sleep(2)
        # welcome_aidant = self.browser.find_element_by_id("welcome_aidant").text
        # self.assertEqual(welcome_aidant, "Bonjour Mélaine Évelyne")


if __name__ == '__main__':
    unittest.main(warnings='ignore')
