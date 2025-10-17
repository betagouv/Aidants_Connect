from django.conf import settings
from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.forms import (
    AidantRequestForm,
    AidantRequestFormSet,
    IssuerForm,
    ReferentForm,
)
from aidants_connect_habilitation.models import Issuer, Manager, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    DraftOrganisationRequestFactory,
    IssuerFactory,
    ManagerFactory,
)
from aidants_connect_habilitation.tests.utils import get_form


@tag("functional", "habilitation")
class ReferentRequestFormViewTests(FunctionalTestCase):

    def setUp(self):
        self.contexts = [
            self.settings(
                GOUV_ADDRESS_SEARCH_API_DISABLED=False,
                GOUV_ADDRESS_SEARCH_API_BASE_URL=(
                    f"{self.live_server_url}{reverse('test_address_api_segur')}"
                ),
            ),
            self.modify_settings(
                CSP_CONNECT_SRC={
                    "append": (
                        f"{self.live_server_url}{reverse('test_address_api_segur')}"
                    )
                },
                CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
            ),
        ]
        for context in self.contexts:
            context.__enter__()

    def tearDown(self):
        for context in self.contexts:
            context.__exit__(None, None, None)

    def test_form_loads_manager_data(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=True, conseiller_numerique=True)
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )
        form = ReferentForm(organisation=organisation)

        self._open_form_url(issuer, organisation)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")
        field_names.remove("conseiller_numerique")

        for field_name in field_names:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR, f"#id_{field_name}"
            )

            self.assertEqual(
                element.get_attribute("value"), getattr(manager, field_name)
            )

    def test_form_modify_manager_data(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=False)
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )
        form = ReferentForm(organisation=organisation)

        self._open_form_url(issuer, organisation)

        new_manager: Manager = ManagerFactory.build(is_aidant=False)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")
        field_names.remove("conseiller_numerique")

        for field_name in field_names:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#id_{field_name}",
            )

            element.clear()
            element.send_keys(str(getattr(new_manager, field_name)))

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        self.wait.until(
            self.path_matches(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            )
        )

        organisation.refresh_from_db()
        saved_manager = organisation.manager

        expected = {}
        actual = {}
        for field_name in form.fields:
            expected[field_name] = getattr(new_manager, field_name)
            actual[field_name] = getattr(saved_manager, field_name)
        self.assertEqual(expected, actual)

    def test_its_me_button_fills_manager_form(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
        )

        form = IssuerForm()

        self._open_form_url(issuer, organisation)
        self.wait.until(self.dsfr_ready())

        for field_name in form.fields:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR, f"[name$='{field_name}']"
            )
            self.assertEqual(element.get_attribute("value"), "")

        self.selenium.find_element(By.CSS_SELECTOR, "#its-me-manager").click()

        # Wait for the JS code to execute
        first_field = list(form.fields)[0]
        self.wait.until(
            expected_conditions.text_to_be_present_in_element_attribute(
                (By.CSS_SELECTOR, f"[name$='{first_field}']"),
                "value",
                getattr(issuer, first_field),
            ),
            "Form does not seem to have been filled",
        )

        for field_name in form.fields:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR, f"[name$='{field_name}']"
            )
            field_value = getattr(issuer, field_name)
            self.assertEqual(element.get_attribute("value"), field_value)

    def _open_form_url(
        self,
        issuer: Issuer,
        organisation_request: OrganisationRequest,
    ):
        self.open_live_url(
            reverse(
                "habilitation_new_referent",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )


@tag("functional")
class PersonnelRequestFormViewTests(FunctionalTestCase):
    submit_css = '[data-test="submit"]'

    def test_form_submit_no_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        self._open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, self.submit_css).click()

        self.wait.until(
            self.path_matches(
                "habilitation_validation",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            )
        )

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 0)

    def test_form_submit_multiple_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        # Setup 2 initial requests
        AidantRequestFactory(organisation=organisation)
        AidantRequestFactory(organisation=organisation)

        self._open_form_url(issuer, organisation)

        formset = AidantRequestFormSet(organisation=organisation)
        for i in range(2, 6):
            aidant_form = get_form(
                AidantRequestForm,
                form_init_kwargs={
                    "organisation": organisation,
                    "auto_id": formset.auto_id,
                    "prefix": formset.add_prefix(i),
                },
            )
            self.fill_form(aidant_form.cleaned_data, aidant_form)
            self.selenium.find_element(By.CSS_SELECTOR, "#partial-submit").click()
            self.wait.until(
                expected_conditions.visibility_of_element_located(
                    (By.ID, f"profile-edit-card-{i}")
                )
            )

        self.selenium.find_element(By.CSS_SELECTOR, self.submit_css).click()

        self.wait.until(
            self.path_matches(
                "habilitation_validation",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            )
        )

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 6)

    def test_form_submit_modify_multiple_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        for _ in range(4):
            AidantRequestFactory(organisation=organisation)

        self._open_form_url(issuer, organisation)
        self.wait.until(self.dsfr_ready())
        self.check_accessibility("habilitation_new_aidants", strict=False)

        modified_aidant_idx = 2
        formset = AidantRequestFormSet(organisation=organisation)
        aidant = formset.forms[modified_aidant_idx].instance
        aidant_form = get_form(
            AidantRequestForm,
            form_init_kwargs={
                "organisation": organisation,
                "auto_id": formset.auto_id,
                "prefix": formset.add_prefix(modified_aidant_idx),
            },
        )

        for field_name in ("first_name", "last_name", "email"):
            self.assertNotEqual(
                getattr(aidant, field_name),
                aidant_form.cleaned_data[field_name],
            )

        self._try_open_modal(By.CSS_SELECTOR, f"#edit-button-{modified_aidant_idx}")
        self.check_accessibility("habilitation_new_aidants_modale", strict=False)

        self.fill_form(
            aidant_form.cleaned_data,
            aidant_form,
            selector=self.selenium.find_element(By.CSS_SELECTOR, "#main-modal"),
        )

        self.selenium.find_element(By.CSS_SELECTOR, "#profile-edit-submit").click()
        self.wait.until(self._modal_closed())
        self.selenium.find_element(By.CSS_SELECTOR, self.submit_css).click()

        self.wait.until(
            self.path_matches(
                "habilitation_validation",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            )
        )
        self.check_accessibility("habilitation_validation", strict=False)

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 4)

        aidant.refresh_from_db()
        for field_name in aidant_form.fields:
            self.assertEqual(
                getattr(aidant, field_name), aidant_form.cleaned_data[field_name]
            )

    def test_cannot_submit_form_without_aidants_displays_errors(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=False)
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )
        self.open_live_url(
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "uuid": organisation.uuid,
                },
            )
        )
        self.selenium.find_element(By.CSS_SELECTOR, self.submit_css).click()

        self.assertEqual(
            self.selenium.find_element(By.CSS_SELECTOR, ".errorlist.nonform").text,
            "Vous devez déclarer au moins 1 aidant si le ou la référente de "
            "l'organisation n'est pas elle-même déclarée comme aidante",
        )

    def _open_form_url(
        self,
        issuer: Issuer,
        organisation_request: OrganisationRequest,
    ):
        self.open_live_url(
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )

    def _modal_closed(self):
        def modal_has_no_open_attr(driver):
            try:
                with self.implicitely_wait(0.1, driver):
                    element_attribute = driver.find_element(
                        By.CSS_SELECTOR, "#main-modal"
                    ).get_attribute("open")
                return element_attribute is None
            except:  # noqa: E722
                return False

        return expected_conditions.all_of(
            expected_conditions.invisibility_of_element_located(
                (By.CSS_SELECTOR, "#main-modal")
            ),
            modal_has_no_open_attr,
        )

    def _try_open_modal(self, by, value: str):
        self._try_close_modal()
        self.js_click(by, value)
        with self.implicitely_wait(0.1):
            self.wait.until(
                expected_conditions.text_to_be_present_in_element_attribute(
                    (By.CSS_SELECTOR, "#main-modal"),
                    "open",
                    "true",
                ),
                "Modal was not opened",
            )

            self.wait.until(
                expected_conditions.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        '#main-modal input[id$="email"]',
                    )
                ),
                "Modal seems opened but form seems not visible",
            )

    def _try_close_modal(self):
        self.wait.until(self.document_loaded())
        self.wait.until(self.dsfr_ready())
        self.js_click(By.TAG_NAME, "body")
        self.wait.until(self._modal_closed(), "Modal seems to be still visible")
