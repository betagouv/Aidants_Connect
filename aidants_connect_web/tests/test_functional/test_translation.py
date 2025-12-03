import time

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_pico_cms.models import MandateTranslation
from aidants_connect_web.tests.factories import AidantFactory


@tag("functional")
class DisplayTranslationTests(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory(post__with_otp_device=True)
        self.lang: MandateTranslation = MandateTranslation.objects.create(
            lang="pus", body="# Test title\n\nTest"
        )

    def test_display_translation_for_espace_aidant_home(self):
        self.open_live_url(reverse("espace_aidant_home"))
        self.login_aidant(self.aidant)

        # Sélecteur plus robuste basé sur l'URL de destination
        mandate_translation_url = reverse("mandate_translation")
        self.selenium.find_element(
            By.CSS_SELECTOR, f"a[href='{mandate_translation_url}']"
        ).click()
        time.sleep(2)

        self.wait.until(self.path_matches("mandate_translation"))
        self.check_accessibility("mandate_translation", strict=True)

        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.CSS_SELECTOR, ".mandate-translation-other"),
                "D’autres langues sont disponibles",
            )
        )

        select = Select(
            self.selenium.find_element(By.CSS_SELECTOR, "#mandate-translation-lang")
        )

        select.select_by_visible_text(self.lang.lang_name)

        translation_container = self.selenium.find_element(
            By.CSS_SELECTOR, ".mandate-translation-other"
        )

        self.assertHTMLEqual(
            f'<section class="container" dir="rtl">{self.lang.to_html()}</section>',
            translation_container.get_attribute("innerHTML"),
        )

        self.assertEqual("pus", translation_container.get_attribute("lang"))
