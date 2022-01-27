from django.test import tag
from selenium.webdriver.common.by import By

from aidants_connect.common.tests.testcases import FunctionalTestCase


@tag("functional")
class HomePage(FunctionalTestCase):
    def test_page_loads(self):
        self.open_live_url("/")
        h1 = self.selenium.find_element(By.TAG_NAME, "h1")
        self.assertEqual(h1.text, "Bienvenue sur Aidants Connect")
