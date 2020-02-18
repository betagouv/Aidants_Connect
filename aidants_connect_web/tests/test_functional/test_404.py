from django.test import tag

from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase


@tag("functional")
class Error404Page(FunctionalTestCase):
    def test_404_page(self):
        self.open_live_url("/thiswontwork")

        h1 = self.selenium.find_element_by_tag_name("h1")
        self.assertEqual(h1.text, "Cette page n’existe pas (404)")
        link_to_home = self.selenium.find_element_by_id("to-home")
        self.assertEqual(link_to_home.text, "Retourner à l’accueil")
