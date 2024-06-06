import os
from os.path import dirname
from os.path import join as path_join

from django.conf import settings
from django.test import tag

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

import aidants_connect_web
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    OrganisationFactory,
)


@tag("functional", "import")
class ImportAidantTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        cls.login_url = f"/{settings.ADMIN_URL}login/"
        cls.import_url = f"/{settings.ADMIN_URL}aidants_connect_web/aidant/import/"
        super().setUpClass()

    def setUp(self) -> None:
        self.organisation = OrganisationFactory(id=4444)
        self.aidant = AidantFactory(
            username="thierry@thierry.com",
            is_superuser=True,
            is_staff=True,
        )
        self.aidant.set_password("laisser-passer-a38")
        self.aidant.save()
        device = self.aidant.staticdevice_set.create()
        device.token_set.create(token="123456")
        WebDriverWait(self.selenium, 10)
        self.login_admin()

    def login_admin(self):
        self.open_live_url(self.login_url)
        login_field = self.selenium.find_element(By.ID, "id_username")
        login_field.send_keys("thierry@thierry.com")
        otp_field = self.selenium.find_element(By.ID, "id_otp_token")
        otp_field.send_keys("123456")
        pwd_field = self.selenium.find_element(By.ID, "id_password")
        pwd_field.send_keys("laisser-passer-a38")

        submit_button = self.selenium.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()
        django_admin_title = self.selenium.find_element(By.TAG_NAME, "h1").text
        self.assertEqual(django_admin_title, "Administration de Django")

    def import_file(self, path):
        self.open_live_url(self.import_url)
        file_import_field = self.selenium.find_element(By.ID, "id_import_file")
        file_import_field.send_keys(path)
        xlsx_type_option = self.selenium.find_element(
            By.XPATH, "//select[@id='id_format']/option[text()='xlsx']"
        )
        xlsx_type_option.click()
        file_import_submit = self.selenium.find_element(
            By.XPATH, "//input[@type='submit']"
        )
        file_import_submit.click()
        try:
            self.selenium.find_element(By.XPATH, "//table[@class='import-preview']")
        except NoSuchElementException:
            first_error = self.selenium.find_element(
                By.XPATH, "//div[@class='errors']/details[1]/summary"
            )
            self.fail(
                f"Import of following file failed: {path} "
                f"with message: '{first_error.text}'"
            )
        file_import_confirm = self.selenium.find_element(By.NAME, "confirm")
        file_import_confirm.click()

    def test_import_correct_files(self):
        excel_fixtures = path_join(
            dirname(aidants_connect_web.__file__),
            "fixtures",
            "import-aidants",
            "correct-files",
        )
        for entry in os.scandir(excel_fixtures):
            if entry.is_file() and entry.path.endswith(".xlsx"):
                self.import_file(entry.path)

    def test_username_and_email_are_trimmed_and_lowercased(self):
        excel_file = path_join(
            dirname(aidants_connect_web.__file__),
            "fixtures",
            "import-aidants",
            "edge-cases",
            "clean-username-and-email.xlsx",
        )

        self.import_file(excel_file)

        self.assertEqual(4, Aidant.objects.count(), "Unexpected count of Aidants in DB")

        aidant_a = Aidant.objects.get(
            first_name="AvecUnEspace", last_name="Après Le Username"
        )
        self.assertEqual("avec.espace@apres.fr", aidant_a.username)
        self.assertEqual("avec.espace@apres.fr", aidant_a.email)

        aidant_b = Aidant.objects.get(
            first_name="UneAdresseMail", last_name="Avec Des Majuscules"
        )
        self.assertEqual("un.email@avec.majuscules.fr", aidant_b.username)
        self.assertEqual("un.email@avec.majuscules.fr", aidant_b.email)

        aidant_c = Aidant.objects.get(
            first_name="UneAdresseMail", last_name="Tout en Majuscules"
        )
        self.assertEqual("un.email@tout.en.majuscules.fr", aidant_c.username)
        self.assertEqual("un.email@tout.en.majuscules.fr", aidant_c.email)

    def test_import_carte_totp(self):
        excel_file = path_join(
            dirname(aidants_connect_web.__file__),
            "fixtures",
            "import-aidants",
            "edge-cases",
            "carte-totp-import.xlsx",
        )
        CarteTOTPFactory(serial_number="TEST01")

        self.import_file(excel_file)

        self.assertEqual(3, Aidant.objects.count(), "Unexpected count of Aidants in DB")

        aidant_a = Aidant.objects.get(username="plop@example.net")
        self.assertTrue(aidant_a.has_a_carte_totp)
        self.assertTrue(aidant_a.has_a_totp_device)

    def test_import_using_datapass_id(self):
        excel_file = path_join(
            dirname(aidants_connect_web.__file__),
            "fixtures",
            "import-aidants",
            "edge-cases",
            "import-by-datapass-id.xlsx",
        )

        orga1 = OrganisationFactory(data_pass_id=5666)
        orga2 = OrganisationFactory(data_pass_id=5667)
        orga3 = OrganisationFactory(data_pass_id=5668)

        self.import_file(excel_file)

        self.assertEqual(5, Aidant.objects.count(), "Unexpected count of Aidants in DB")

        aidant1 = Aidant.objects.get(username="aidant1@toto.net")
        self.assertEqual(aidant1.organisation, orga1)

        respo1 = Aidant.objects.get(username="respo1@toto.net")
        self.assertEqual(aidant1.organisation, orga1)
        self.assertIn(orga1, respo1.responsable_de.all())

        respo2 = Aidant.objects.get(username="respo2@toto.net")
        respo2_respo = respo2.responsable_de.all()
        for org in (orga1, orga2):
            self.assertIn(org, respo2_respo)

        respo3 = Aidant.objects.get(username="respo3@toto.net")
        respo3_respo = respo3.responsable_de.all()
        for org in (orga1, orga2, orga3):
            self.assertIn(org, respo3_respo)
