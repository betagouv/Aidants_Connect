from random import randint
from typing import List
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import modify_settings, override_settings, tag
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_common.utils.gouv_address_api import Address
from aidants_connect_habilitation.forms import (
    AidantRequestForm,
    IssuerForm,
    ManagerForm,
    PersonnelForm,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    Manager,
    OrganisationRequest,
)
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    DraftOrganisationRequestFactory,
    IssuerFactory,
    ManagerFactory,
)
from aidants_connect_habilitation.tests.utils import get_form, load_json_fixture

FIXED_PORT = randint(8081, 8179)


def _django_server_url(path):
    return f"http://localhost:{FIXED_PORT}{path}"


@tag("functional")
class PersonnelRequestFormViewTests(FunctionalTestCase):
    port = FIXED_PORT

    def test_js_managment_form_aidant_count_is_modified(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )
        self._open_form_url(issuer, organisation)

        input_el = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name$='TOTAL_FORMS']"
        )

        for i in range(1, 5):
            self.assertEqual(str(i), input_el.get_attribute("value"))
            self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
            self.assertEqual(str(i + 1), input_el.get_attribute("value"))

    def test_js_aidant_form_is_added_to_formset(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )
        self._open_form_url(issuer, organisation)

        for i in range(1, 5):
            input_el = self.selenium.find_elements(
                By.CSS_SELECTOR, ".aidant-form-container"
            )
            self.assertEqual(i, len(input_el))
            self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
            input_el = self.selenium.find_elements(
                By.CSS_SELECTOR, ".aidant-form-container"
            )
            self.assertEqual(i + 1, len(input_el))

    def test_js_hide_add_aidant_form_button_on_max(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )
        self._open_form_url(issuer, organisation)

        add_aidant_button = self.selenium.find_element(
            By.CSS_SELECTOR, "#add-aidant-btn"
        )

        max_value = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name$='MAX_NUM_FORMS']"
        ).get_attribute("value")

        # Manually set the number of forms to the max - 1 for the Stimulus controller
        self.selenium.execute_script(
            """document.querySelector("[data-controller='personnel-form']")"""
            f""".dataset.personnelFormFormCountValue = {int(max_value) - 1}"""
        )

        self.assertTrue(add_aidant_button.is_displayed())
        add_aidant_button.click()
        self.assertFalse(add_aidant_button.is_displayed())

    def test_js_added_aidant_form_has_correct_id(self):
        """
        This test verifies that the JS code generates forms exactly like
        AidantRequestFormSet would.
        """
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )

        self._open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()

        form_elts = self.selenium.find_elements(
            By.CSS_SELECTOR, ".aidant-form-container"
        )

        self.assertEqual(len(form_elts), 4)

        form = AidantRequestForm(organisation=organisation)

        for i, _ in enumerate(form_elts):
            for field_name, field in form.fields.items():
                html_id = f"id_{PersonnelForm.AIDANTS_FORMSET_PREFIX}-{i}-{field_name}"

                try:
                    field_label = self.selenium.find_element(
                        By.CSS_SELECTOR, f'[for="{html_id}"]'
                    )
                except NoSuchElementException:
                    self.fail(
                        f"Label for form element {html_id} not found. "
                        "Was form 'prefix' or 'auto_id' modified?"
                    )

                self.assertEqual(field_label.text, field.label)

    def test_form_loads_manager_data(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=True)
        form = ManagerForm()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        self._open_form_url(issuer, organisation)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")
        field_names.remove("alternative_address")
        field_names.remove("skip_address_validation")

        element: WebElement = self.selenium.find_element(
            By.XPATH,
            f"//*[@id='id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant']"
            "//option[normalize-space(text())='Oui']",
        )

        self.assertIsNotNone(
            element.get_attribute("selected"),
            "Manager is also an aidant, option should have been checked",
        )

        for field_name in field_names:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#id_{PersonnelForm.MANAGER_FORM_PREFIX}-{field_name}",
            )

            self.assertEqual(
                element.get_attribute("value"), getattr(manager, field_name)
            )

    def test_form_modify_manager_data(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=False)
        form = ManagerForm()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
        )

        self._open_form_url(issuer, organisation)

        new_manager: Manager = ManagerFactory.build(is_aidant=True)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")
        field_names.remove("alternative_address")
        field_names.remove("skip_address_validation")

        self.assertIsNone(
            self.selenium.find_element(
                By.XPATH,
                f"//*[@id='id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant']"
                "//option[normalize-space(text())='Oui']",
            ).get_attribute("selected"),
            "Manager is not an aidant, checkbox should not have been checked",
        )

        Select(
            self.selenium.find_element(
                By.ID, f"id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant"
            )
        ).select_by_visible_text("Oui")

        self.assertIsNotNone(
            self.selenium.find_element(
                By.XPATH,
                f"//*[@id='id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant']"
                "//option[normalize-space(text())='Oui']",
            ).get_attribute("selected"),
            "New manager is an aidant, checkbox should be checked",
        )

        for field_name in field_names:
            if field_name not in ["city_insee_code", "department_insee_code"]:
                element: WebElement = self.selenium.find_element(
                    By.CSS_SELECTOR,
                    f"#id_{PersonnelForm.MANAGER_FORM_PREFIX}-{field_name}",
                )
                element.clear()
                element.send_keys(str(getattr(new_manager, field_name)))

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        saved_manager = organisation.manager

        for field_name in form.fields:
            if field_name not in ["alternative_address", "skip_address_validation"]:
                self.assertEqual(
                    getattr(saved_manager, field_name), getattr(new_manager, field_name)
                )

    def test_form_submit_no_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
        )

        self._open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 0)

    def test_form_submit_multiple_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
        )

        # Setup 2 initial requests
        AidantRequestFactory(organisation=organisation)
        AidantRequestFactory(organisation=organisation)

        self._open_form_url(issuer, organisation)

        for i in range(2, 6):
            aidant_form: AidantRequestForm = get_form(
                AidantRequestForm, form_init_kwargs={"organisation": organisation}
            )
            aidant_data = aidant_form.cleaned_data
            for field_name in aidant_form.fields:
                element: WebElement = self.selenium.find_element(
                    By.CSS_SELECTOR,
                    f"#id_{PersonnelForm.AIDANTS_FORMSET_PREFIX}-{i}-{field_name}",
                )
                element.clear()
                element.send_keys(aidant_data[field_name])

            self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 6)

    def test_form_submit_modify_multiple_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
        )

        for _ in range(4):
            AidantRequestFactory(organisation=organisation)

        self._open_form_url(issuer, organisation)

        modified_aidant_idx = 2
        modified_aidant_email = self.selenium.find_element(
            By.CSS_SELECTOR,
            f"#id_{PersonnelForm.AIDANTS_FORMSET_PREFIX}-{modified_aidant_idx}-email",
        ).get_attribute("value")

        new_aidant_form: AidantRequestForm = get_form(
            AidantRequestForm, form_init_kwargs={"organisation": organisation}
        )
        aidant_data = new_aidant_form.cleaned_data
        for field_name in new_aidant_form.fields:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#id_{PersonnelForm.AIDANTS_FORMSET_PREFIX}-"
                f"{modified_aidant_idx}-{field_name}",
            )
            element.clear()
            element.send_keys(aidant_data[field_name])

        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 4)

        with self.assertRaises(AidantRequest.DoesNotExist):
            AidantRequest.objects.get(email=modified_aidant_email)

        saved_aidant = organisation.aidant_requests.get(email=aidant_data["email"])
        for field_name in new_aidant_form.fields:
            self.assertEqual(getattr(saved_aidant, field_name), aidant_data[field_name])

    def test_js_its_me_button_fills_manager_form(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
        )

        form = IssuerForm()

        self._open_form_url(issuer, organisation)

        for field_name in form.fields:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR, f"#manager-subform [name$='{field_name}']"
            )
            self.assertEqual(element.get_attribute("value"), "")

        self.selenium.find_element(By.CSS_SELECTOR, "#its-me-manager").click()

        for field_name in form.fields:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR, f"#manager-subform [name$='{field_name}']"
            )
            field_value = getattr(issuer, field_name)
            self.assertEqual(element.get_attribute("value"), field_value)

    def test_cannot_submit_form_without_aidants_displays_errors(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=False)
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )
        self._open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        error_element = self.selenium.find_element(
            By.CSS_SELECTOR, ".aidant-forms p.errorlist"
        )

        self.assertEqual(
            error_element.text,
            "Vous devez déclarer au moins 1 aidant si le ou la responsable de "
            "l'organisation n'est pas elle-même déclarée comme aidante",
        )

        error_element = self.selenium.find_element(
            By.CSS_SELECTOR, "#manager-subform p.errorlist"
        )

        self.assertEqual(
            error_element.text,
            "Veuillez cocher cette case ou déclarer au moins un aidant ci-dessous",
        )

        error_element = self.selenium.find_element(
            By.CSS_SELECTOR, ".aidant-forms p.errorlist"
        )

        self.assertEqual(
            error_element.text,
            "Vous devez déclarer au moins 1 aidant si le ou la responsable de "
            "l'organisation n'est pas elle-même déclarée comme aidante",
        )

    @override_settings(
        GOUV_ADDRESS_SEARCH_API_DISABLED=False,
        GOUV_ADDRESS_SEARCH_API_BASE_URL=_django_server_url(
            reverse("test_address_api_segur")
        ),
    )
    @modify_settings(
        CSP_CONNECT_SRC={
            "append": _django_server_url(reverse("test_address_api_segur"))
        },
        CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
    )
    def test_js_I_must_select_a_correct_address(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )

        manager: Manager = ManagerFactory.build(
            address="15 avenue de segur", zipcode="", city=""
        )

        self._open_form_url(issuer, organisation)

        # Fill form
        for item in [
            "last_name",
            "first_name",
            "email",
            "phone",
            "address",
            "profession",
        ]:
            value = str(getattr(manager, item))
            selector = f"#id_{PersonnelForm.MANAGER_FORM_PREFIX}-{item}"
            self.selenium.find_element(By.CSS_SELECTOR, selector).send_keys(value)

        Select(
            self.selenium.find_element(
                By.ID, f"id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant"
            )
        ).select_by_visible_text("Oui")

        # Open dropdown
        self.selenium.find_element(By.CSS_SELECTOR, "#id_manager-address").click()

        selected_address = "Avenue de Ségur 75007 Paris"
        # Select result
        self.selenium.find_element(
            By.XPATH, f"//*[normalize-space(text())='{selected_address}']"
        ).click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        manager = organisation.manager
        self.assertEqual(manager.address, "Avenue de Ségur")
        self.assertEqual(manager.zipcode, "75007")
        self.assertEqual(manager.city, "Paris")
        self.assertEqual(manager.city_insee_code, "75107")

    @override_settings(
        GOUV_ADDRESS_SEARCH_API_DISABLED=False,
        GOUV_ADDRESS_SEARCH_API_BASE_URL=_django_server_url(
            reverse("test_address_api_no_result")
        ),
    )
    @modify_settings(
        CSP_CONNECT_SRC={
            "append": _django_server_url(reverse("test_address_api_no_result"))
        },
        CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
    )
    def test_js_I_can_submit_an_address_that_is_not_found(self):
        address = "15 avenue de segur"
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )

        manager: Manager = ManagerFactory.build(
            address=address, zipcode="37000", city="Orléans"
        )

        self._open_form_url(issuer, organisation)

        # Fill form
        for item in [
            "last_name",
            "first_name",
            "email",
            "phone",
            "address",
            "profession",
            "zipcode",
            "city",
        ]:
            value = str(getattr(manager, item))
            selector = f"#id_{PersonnelForm.MANAGER_FORM_PREFIX}-{item}"
            self.selenium.find_element(By.CSS_SELECTOR, selector).send_keys(value)

        Select(
            self.selenium.find_element(
                By.ID, f"id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant"
            )
        ).select_by_visible_text("Oui")

        # Open dropdown
        self.selenium.find_element(By.CSS_SELECTOR, "#id_manager-address").click()

        self.assertEqual(
            f"Aucun résultat trouvé pour la requête « {address} »",
            self.selenium.find_element(By.CSS_SELECTOR, ".no-result").text,
        )

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        manager = organisation.manager
        self.assertEqual(manager.address, "15 avenue de segur")
        self.assertEqual(manager.zipcode, "37000")
        self.assertEqual(manager.city, "Orléans")

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


@tag("functional")
class PersonnelRequestFormViewNoJSTests(FunctionalTestCase):
    js = False

    @override_settings(GOUV_ADDRESS_SEARCH_API_DISABLED=False)
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_I_must_select_a_correct_address(self, search_adresses_mock: Mock):
        expected_address = "Rue de Paris 45000 Orléans"
        selected_address = "Rue du Parc 45000 Orléans"

        def search_adresses(query_string: str) -> List[Address]:
            if query_string == expected_address:
                result = [
                    Address(**item["properties"])
                    for item in load_json_fixture("address_results.json")["features"]
                ]
                return result

            self.fail(f"Expected manager with address '{expected_address}'")

        search_adresses_mock.side_effect = search_adresses

        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(
            address="Rue de Paris", zipcode="45000", city="Orléans"
        )
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        self._open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        self.selenium.find_element(
            By.XPATH,
            "//*[@id='id_manager-alternative_address']"
            f"//*[normalize-space(text())='{selected_address}']",
        ).click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        manager.refresh_from_db()
        self.assertEqual(
            selected_address, f"{manager.address} {manager.zipcode} {manager.city}"
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
