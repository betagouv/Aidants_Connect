from urllib.parse import urlencode

from django.conf import settings

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    visibility_of_any_elements_located,
)

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Usager
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)


class IdProviderTest(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory(post__with_otp_device=True)

        self.usager_josephine: Usager = UsagerFactory(
            given_name="Joséphine", family_name="ST-PIERRE"
        )

        self.usager_anne: Usager = UsagerFactory(
            given_name="Anne Cécile Gertrude", family_name="EVALOUS"
        )

        self.usager_corentin: Usager = UsagerFactory(
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
        self.login_aidant(self.aidant)

        self._select_user("Jose", self.usager_josephine)

    def test_change_user(self):
        self.open_live_url(f"/authorize/?{self.url_parameters}")
        self.login_aidant(self.aidant)

        self._select_user("Jose", self.usager_josephine)

        self.selenium.find_element(By.CSS_SELECTOR, ".change-user").click()

        self._select_user("Coren", self.usager_corentin)

    def test_user_list(self):
        self.open_live_url(f"/authorize/?{self.url_parameters}")
        self.login_aidant(self.aidant)

        # Open the dropdown
        self.selenium.find_element(By.CSS_SELECTOR, ".fr-accordion.user-detail").click()

        self.wait.until(
            visibility_of_any_elements_located([By.CSS_SELECTOR, ".user-detail-item"])
        )

        items = self.selenium.find_elements(By.CSS_SELECTOR, ".user-detail-item")
        self.assertEqual(3, len([e for e in items if e.is_displayed()]))

        self.selenium.find_element(
            By.CSS_SELECTOR, f"[data-user-id='{self.usager_anne.pk}']"
        ).click()

        self.wait.until(self.path_matches("fi_select_demarche"))

        self.selenium.find_element(By.CSS_SELECTOR, ".instructions")

        self.assertInHTML(
            self.usager_anne.get_full_name(),
            self.selenium.find_element(By.CSS_SELECTOR, ".instructions").get_attribute(
                "innerHTML"
            ),
        )

    def _select_user(self, search_text: str, selected_user: Usager):
        autocomplete = self.selenium.find_element(By.ID, "anonymous-filter-input")
        autocomplete.send_keys(search_text)
        usager = self.selenium.find_element(
            By.XPATH, f"//li[@data-value='{selected_user.id}']"
        )
        usager.click()

        button = self.selenium.find_element(By.ID, "submit-button")

        button.click()

        self.wait.until(self.path_matches("fi_select_demarche"))
