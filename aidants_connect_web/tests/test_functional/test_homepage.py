from django.test import tag

from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase


@tag("functional")
class HomePage(FunctionalTestCase):
    def test_page_loads(self):
        self.open_live_url("/")
        h1 = self.selenium.find_element_by_tag_name("h1")
        self.assertEqual(h1.text, "Bienvenue sur Aidants Connect")
