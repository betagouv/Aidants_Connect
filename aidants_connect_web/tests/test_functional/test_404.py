from django.test import tag

from selenium.webdriver.common.by import By

from aidants_connect.common.tests.testcases import FunctionalTestCase


@tag("functional")
class Error404Page(FunctionalTestCase):
    def test_404_page(self):
        self.open_live_url("/thiswontwork")

        h1 = self.selenium.find_element(By.TAG_NAME, "h1")
        self.assertEqual(h1.text, "Cette page n’existe pas (404)")
        link_to_home = self.selenium.find_element(By.ID, "to-home")
        self.assertEqual(link_to_home.text, "Retourner à l’accueil")
