from django.conf import settings
from django.test import tag

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.models import Region
from aidants_connect_common.tests.factories import DepartmentFactory, RegionFactory
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


class RegionFilterTestCase(FunctionalTestCase):
    def setUp(self):
        self.login_url = f"/{settings.ADMIN_URL}login/"
        self.organisation_url = (
            f"/{settings.ADMIN_URL}aidants_connect_web/organisation/"
        )
        self.login_admin()

        if Region.objects.filter(name="Île-de-France").exists():
            return

        region_idf = RegionFactory(name="Île-de-France")
        region_mayotte = RegionFactory(name="Mayotte")
        region_grandest = RegionFactory(name="Grand Est")

        DepartmentFactory(name="Yvelines", zipcode="78", region=region_idf)
        DepartmentFactory(name="Mayotte", zipcode="976", region=region_mayotte)
        DepartmentFactory(name="Bas-Rhin", zipcode="67", region=region_grandest)
        DepartmentFactory(
            depname_name="Haut-Rhin", zipcode="68", region=region_grandest
        )

    def login_admin(self):
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


@tag("functional", "import")
class OrganisationFilterTests(RegionFilterTestCase):
    def setUp(self):
        super().setUp()
        self.organisation_url = (
            f"/{settings.ADMIN_URL}aidants_connect_web/organisation/"
        )

        OrganisationFactory(zipcode=78123, name="Orga des Yvelines")
        OrganisationFactory(zipcode=67999, name="Orga du Bas-Rhin")
        OrganisationFactory(zipcode=68123, name="Orga du Haut-Rhin")
        OrganisationFactory(zipcode=0, name="Sans Code Postal")

        OrganisationFactory(data_pass_id=666, name="Avec ID Datapass")
        OrganisationFactory(name="Sans ID Datapass")

    def test_region_and_other_filter(self):
        self.open_live_url(self.organisation_url)
        self.assertTrue("Orga des Yvelines" in self.selenium.page_source)
        self.assertTrue("Orga du Bas-Rhin" in self.selenium.page_source)
        self.assertTrue("Sans Code Postal" in self.selenium.page_source)
        idf_link = self.selenium.find_element(By.LINK_TEXT, "Île-de-France")
        idf_link.click()

        self.assertTrue(
            "Orga des Yvelines" in self.selenium.page_source,
        )
        self.assertFalse(
            "Orga du Bas-Rhin" in self.selenium.page_source,
        )
        self.assertFalse("Sans Code Postal" in self.selenium.page_source)
        grandest_link = self.selenium.find_element(By.LINK_TEXT, "Grand Est")
        grandest_link.click()
        self.assertFalse(
            "Orga des Yvelines" in self.selenium.page_source,
            "Orga des Yvelines should not appear after filter on grand est",
        )
        self.assertTrue(
            "Orga du Bas-Rhin" in self.selenium.page_source,
            "Orga du Bas-Rhin is not there, it should",
        )
        self.assertTrue(
            "Orga du Haut-Rhin" in self.selenium.page_source,
            "Orga du Haut-Rhin is not there, it should",
        )
        other_link = self.selenium.find_element(By.XPATH, "//a[@href='?region=other']")
        other_link.click()
        self.assertFalse("Orga du Bas-Rhin" in self.selenium.page_source)
        self.assertTrue("Sans Code Postal" in self.selenium.page_source)

    def test_datapass_id_filter(self):
        self.open_live_url(self.organisation_url)
        self.assertTrue("Avec ID Datapass" in self.selenium.page_source)
        self.assertTrue("Sans ID Datapass" in self.selenium.page_source)
        idf_link = self.selenium.find_element(By.LINK_TEXT, "Sans n° Datapass")
        idf_link.click()

        self.assertFalse("Avec ID Datapass" in self.selenium.page_source)
        self.assertTrue("Sans ID Datapass" in self.selenium.page_source)


class AidantFilterTestCase(RegionFilterTestCase):
    def setUp(self):
        super().setUp()
        self.aidant_url = f"/{settings.ADMIN_URL}aidants_connect_web/aidant/"

        orga_basrhin = OrganisationFactory(zipcode=67999, name="Orga du Bas-Rhin")
        orga_other = OrganisationFactory(zipcode=0, name="Sans Code Postal")

        self.aidant_basrhin = AidantFactory(
            last_name="Du Bas-Rhin", organisation=orga_basrhin
        )
        self.aidant_other = AidantFactory(
            last_name="D'on ne sait où", organisation=orga_other
        )

    def test_region_and_other_filter(self):
        self.open_live_url(self.aidant_url)
        self.assertTrue("Du Bas-Rhin" in self.selenium.page_source)
        self.assertTrue("D'on ne sait où" in self.selenium.page_source)
        other_link = self.selenium.find_element(By.LINK_TEXT, "Autre")
        other_link.click()
        self.assertFalse("Du Bas-Rhin" in self.selenium.page_source)
        self.assertTrue("D'on ne sait où" in self.selenium.page_source)
        grand_est_link = self.selenium.find_element(By.LINK_TEXT, "Grand Est")
        grand_est_link.click()
        self.assertTrue("Du Bas-Rhin" in self.selenium.page_source)
        self.assertFalse("D'on ne sait où" in self.selenium.page_source)


class HabilitationRequestTestCase(RegionFilterTestCase):
    def setUp(self):
        super().setUp()
        self.hab_request_url = (
            f"/{settings.ADMIN_URL}aidants_connect_web/habilitationrequest/"
        )

        orga_basrhin = OrganisationFactory(zipcode=67999, name="Orga du Bas-Rhin")
        orga_other = OrganisationFactory(zipcode=0, name="Sans Code Postal")

        self.hab_request_basrhin = HabilitationRequestFactory(
            last_name="Du Bas-Rhin", organisation=orga_basrhin
        )
        self.hab_request_other = HabilitationRequestFactory(
            last_name="D'on ne sait où", organisation=orga_other
        )

    def test_region_and_other_filter(self):
        self.open_live_url(self.hab_request_url)
        self.assertTrue("Du Bas-Rhin" in self.selenium.page_source)
        self.assertTrue("D'on ne sait où" in self.selenium.page_source)
        # cannot simply click on "Autre" because there is another "Autre" option
        # (in "origin" filter)
        other_link = self.selenium.find_element(By.XPATH, "//a[@href='?region=other']")
        other_link.click()

        self.assertFalse("Du Bas-Rhin" in self.selenium.page_source)
        self.assertTrue("D'on ne sait où" in self.selenium.page_source)
        grand_est_link = self.selenium.find_element(By.LINK_TEXT, "Grand Est")
        grand_est_link.click()

        self.assertTrue("Du Bas-Rhin" in self.selenium.page_source)
        self.assertFalse("D'on ne sait où" in self.selenium.page_source)
