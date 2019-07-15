from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver


class Error404Page(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/thiswontwork")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_404_page(self):
        H1 = self.selenium.find_element_by_tag_name("h1")
        self.assertEqual(H1.text, "Cette page n’existe pas (404)")
        link_to_home = self.selenium.find_element_by_id("to-home")
        self.assertEqual(link_to_home.text, "Retourner à l’accueil")
