from django.conf import settings
from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory


@tag("functional")
class ValidateCGUTests(FunctionalTestCase):
    def setUp(self):
        self.aidant: Aidant = AidantFactory(
            email="thierry@thierry.com",
            validated_cgu_version=None,
            post__with_otp_device=True,
        )

    def test_validate_cgu(self):
        self.open_live_url(reverse("espace_aidant_cgu"))

        # Login
        self.login_aidant(self.aidant)

        self.assertIsNone(self.aidant.validated_cgu_version)
        self.check_accessibility("espace_aidant_cgu", strict=True)

        # Espace Aidant home
        self.selenium.find_element(By.CSS_SELECTOR, 'label[for="id_agree"]').click()
        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.wait.until(self.path_matches("espace_aidant_home"))
        self.check_accessibility("espace_aidant_home", strict=True)

        el = self.selenium.find_element(
            By.XPATH, "//*[contains(@class, 'fr-alert') and contains(., 'CGU')]"
        )
        self.assertEqual(
            "Les CGU Aidants Connect ont été validées avec succès.", el.text.strip()
        )

        self.aidant.refresh_from_db()
        self.assertEqual(
            settings.CGU_CURRENT_VERSION, self.aidant.validated_cgu_version
        )
