from django.test import tag
from selenium.webdriver.common.by import By

from aidants_connect.common.tests.testcases import FunctionalTestCase
from selenium.common.exceptions import NoSuchElementException


@tag("functional", "a11y")  # nb: a11y stands for "accessibility"
class Accessibility(FunctionalTestCase):
    def test_skiplinks_are_valid(self):
        self.open_live_url("/")

        skip_links = self.selenium.find_elements(By.CSS_SELECTOR, ".skip-links a[href]")

        self.assertGreaterEqual(len(skip_links), 1, "No skip links were found")

        for skip_link in skip_links:
            url = skip_link.get_attribute("href")
            id = url.split("#")[1]
            try:
                self.selenium.find_element(By.ID, id)
            except NoSuchElementException:
                self.fail(
                    f'Skiplink "{skip_link.get_attribute("textContent")}"'
                    f"points to non-existing element #{id}"
                )
