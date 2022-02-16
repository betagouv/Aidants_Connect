from django.test import tag

from selenium.webdriver.common.by import By

from aidants_connect.common.tests.testcases import FunctionalTestCase


@tag("functional")
class StatistiquesPage(FunctionalTestCase):
    def test_page_loads(self):
        self.open_live_url("/stats/")
        self.assertEqual(len(self.selenium.find_elements_by_class_name("tile")), 7)