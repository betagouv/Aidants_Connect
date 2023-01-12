from urllib.parse import urlencode

from django.conf import settings

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_contains
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.tests.test_functional.utilities import login_aidant


class IdProviderTest(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory(
            email="thierry@thierry.com", post__with_otp_device=True
        )

        self.usager_josephine = UsagerFactory(
            given_name="Joséphine", family_name="ST-PIERRE"
        )

        self.usager_anne = UsagerFactory(
            given_name="Anne Cécile Gertrude", family_name="EVALOUS"
        )

        self.usager_corentin = UsagerFactory(
            given_name="Corentin", family_name="Dupont", preferred_username="Anne"
        )

        self.url_parameters = urlencode(
            {
                "state": 1234,
                "nonce": 1234,
                "response_type": "code",
                "client_id": settings.FC_AS_FI_ID,
                "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
                "scope": "openid profile email address phone birth",
                "acr_values": "eidas1",
            }
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_josephine,
            post__create_authorisations=["argent", "famille"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_corentin,
            post__create_authorisations=["argent", "famille", "logement"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_anne,
            post__create_authorisations=["argent", "famille", "logement"],
        )

    def test_search_feature(self):
        self.open_live_url(f"/authorize/?{self.url_parameters}")

        login_aidant(self)

        autocomplete = self.selenium.find_element(By.ID, "filter-input")
        autocomplete.send_keys("Jose")
        usager = self.selenium.find_element(
            By.XPATH, f"//li[@data-value='{self.usager_josephine.id}']"
        )
        usager.click()

        button = self.selenium.find_element(By.ID, "submit-button")

        button.click()
        wait = WebDriverWait(self.selenium, 10)

        wait.until(url_contains("/select_demarche/"))
