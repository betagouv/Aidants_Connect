from selenium import webdriver
import unittest


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
        fc_button = self.browser.find_element_by_id("bouton_fc")
        fc_button_link = fc_button.get_attribute("href")
        self.assertIn("fc_authorize", fc_button_link)
        fc_button.click()
        fc_title = self.browser.title
        self.assertEqual("Connexion - choix du compte", fc_title)


if __name__ == '__main__':
    unittest.main(warnings='ignore')
