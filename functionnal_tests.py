from selenium import webdriver
import unittest
import time


class NewVisitorConnection(unittest.TestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.get("http://localhost:1337")

    def tearDown(self):
        self.browser.quit()

    def test_page_loads(self):
        welcome_aidant = self.browser.find_element_by_id("welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bienvenue, aidant")

    def test_aidant_login(self):
        # Enter credentials
        email_input = self.browser.find_element_by_id("email")

        # Login to switchboard
        # Fill in form
        # Get Usager's identité privot


    def test_fc_button(self):
        # Click on the FranceConnect button
        fc_button = self.browser.find_element_by_id("bouton_fc")
        fc_button_link = fc_button.get_attribute("href")
        self.assertIn("fc_authorize", fc_button_link)
        fc_button.click()
        time.sleep(5)

        # Click on the 'Démonstration' identity provider
        fc_title = self.browser.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        demonstration_hex = self.browser.find_elements_by_class_name("hexLink")[1]
        demonstration_hex.click()
        time.sleep(5)

        # Use the Aidant credentials (Mélaine)

        demo_title = self.browser.find_element_by_tag_name("h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        submit_button = self.browser.find_elements_by_tag_name("input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        time.sleep(5)
        welcome_aidant = self.browser.find_element_by_id("welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bonjour Mélaine Évelyne")
        time.sleep(5)
        # Click on the FranceConnect button for usager
        fc_button = self.browser.find_element_by_id("bouton_fc")
        fc_button_link = fc_button.get_attribute("href")
        self.assertIn("fc_authorize", fc_button_link)
        fc_button.click()
        time.sleep(5)

        # Click on the 'Démonstration' identity provider
        fc_title = self.browser.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        demonstration_hex = self.browser.find_elements_by_class_name("hexLink")[0]
        demonstration_hex.click()
        time.sleep(5)

        # Use the Usager credentials with a different FI (mercier_eric@mail.com)

        demo_tag = self.browser.find_element_by_tag_name("h2").text
        self.assertEqual(demo_tag, "J'accède avec mon mot de passe")
        numero_fiscal_input = self.browser.find_element_by_id("LMDP_Spi_tmp")
        numero_fiscal_input.send_keys("1234567891011")
        password_input = self.browser.find_element_by_id("LMDP_Password_tmp")
        password_input.send_keys("123")

        submit_button = self.browser.find_element_by_id("valider")
        submit_button.click()
        time.sleep(5)

        # Get Usager's identité privot

        json = self.browser.find_element_by_tag_name("body").text
        self.assertIn('given_name "Eric"', json)


if __name__ == "__main__":
    unittest.main(warnings="ignore")
