from selenium import webdriver
import unittest


class NewVisitorConnection(unittest.TestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.get("http://localhost:8000/authorize?state=34")

    def tearDown(self):
        self.browser.quit()

    def test_page_loads(self):
        welcome_aidant = self.browser.find_element_by_id("welcome_aidant").text
        self.assertEqual(welcome_aidant, "Bienvenue, aidant")
        # button = self.browser.find_element_by_id("submit")


if __name__ == "__main__":
    unittest.main(warnings="ignore")
