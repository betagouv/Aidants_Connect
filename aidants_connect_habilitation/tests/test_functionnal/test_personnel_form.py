from typing import List
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import override_settings, tag
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_common.utils.gouv_address_api import Address
from aidants_connect_habilitation.forms import (
    AidantRequestFormLegacy,
    IssuerForm,
    ManagerForm,
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


@tag("functional")
class ReferentRequestFormViewTests(FunctionalTestCase):
    def test_form_loads_manager_data(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory(is_aidant=True, conseiller_numerique=True)
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )
        form = ManagerForm(organisation=organisation)

        self._open_form_url(issuer, organisation)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")
        field_names.remove("conseiller_numerique")
        field_names.remove("alternative_address")
        field_names.remove("skip_address_validation")

        element: WebElement = self.selenium.find_element(
            By.XPATH,
            "//*[@id='id_is_aidant']//option[normalize-space(text())='Oui']",
        )

        self.assertIsNotNone(
            element.get_attribute("selected"),
            "Manager is also an aidant, option should have been checked",
        )

        self.assertIsNotNone(
            self.selenium.find_element(
                By.CSS_SELECTOR, '#id_conseiller_numerique [value="True"]'
            ).get_attribute("checked"),
            "Manager is also conseiller numérique, option should have been checked",
        )

        for field_name in field_names:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#manager-subform #id_{field_name}",
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
        form = ManagerForm(organisation=organisation)

        self._open_form_url(issuer, organisation)

        new_manager: Manager = ManagerFactory.build(is_aidant=True)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")
        field_names.remove("conseiller_numerique")
        field_names.remove("alternative_address")
        field_names.remove("skip_address_validation")

        self.assertIsNone(
            self.selenium.find_element(
                By.XPATH,
                "//*[@id='id_is_aidant']//*[normalize-space(text())='Oui']",
                # noqa: E501
            ).get_attribute("selected"),
            "Manager is not an aidant, checkbox should not have been checked",
        )

        Select(
            self.selenium.find_element(By.ID, "id_is_aidant")
        ).select_by_visible_text("Oui")

        self.assertIsNotNone(
            self.selenium.find_element(
                By.XPATH,
                "//*[@id='id_is_aidant']//*[normalize-space(text())='Oui']",
                # noqa: E501
            ).get_attribute("selected"),
            "Manager is not an aidant, checkbox should not have been checked",
        )

        for field_name in field_names:
            if field_name not in ["city_insee_code", "department_insee_code"]:
                element: WebElement = self.selenium.find_element(
                    By.CSS_SELECTOR,
                    f"#manager-subform #id_{field_name}",
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

        for field_name in form.fields:
            if field_name not in (
                "alternative_address",
                "skip_address_validation",
                "conseiller_numerique",
            ):
                self.assertEqual(
                    getattr(saved_manager, field_name), getattr(new_manager, field_name)
                )

    def test_issuer_form_is_rendered_harmless(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
        )

        self._open_form_url(issuer, organisation)

        for name in IssuerForm().fields.keys():
            el_id = f"id_{name}"
            el = self.selenium.find_element(By.ID, el_id)
            el_name_attr = el.get_attribute("name")
            self.assertEqual(
                el_name_attr,
                "",
                f"""Element <{el.tag_name} id="{el_id}"> from issuer form should not """
                f"have `name` attribute set (current value is '{el_name_attr}')",
            )

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

        for field_name in ("zipcode", "city", "address"):
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR, f"#manager-subform [name$='{field_name}']"
            )
            field_value = getattr(organisation, field_name)
            self.assertEqual(element.get_attribute("value"), field_value)

    def test_js_I_must_select_a_correct_address(self):
        with self.settings(
            GOUV_ADDRESS_SEARCH_API_DISABLED=False,
            GOUV_ADDRESS_SEARCH_API_BASE_URL=(
                f"{self.live_server_url}{reverse('test_address_api_segur')}"
            ),
        ):
            with self.modify_settings(
                CSP_CONNECT_SRC={
                    "append": (
                        f"{self.live_server_url}{reverse('test_address_api_segur')}"
                    )
                },
                CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
            ):
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
                    self.selenium.find_element(
                        By.CSS_SELECTOR, f"#manager-subform #id_{item}"
                    ).send_keys(value)

                Select(
                    self.selenium.find_element(By.ID, "id_is_aidant")
                ).select_by_visible_text("Oui")

                self.selenium.find_element(
                    By.CSS_SELECTOR,
                    '#id_conseiller_numerique [value="False"]',
                ).click()

                # Open dropdown
                self.selenium.find_element(
                    By.CSS_SELECTOR, "#manager-subform #id_address"
                ).click()

                selected_address = "Avenue de Ségur 75007 Paris"
                # Select result
                self.selenium.find_element(
                    By.XPATH, f"//*[contains(text(),'{selected_address}')]"
                ).click()

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
                manager = organisation.manager
                self.assertEqual(manager.address, "Avenue de Ségur")
                self.assertEqual(manager.zipcode, "75007")
                self.assertEqual(manager.city, "Paris")
                self.assertEqual(manager.city_insee_code, "75107")

    def test_js_I_can_submit_an_address_that_is_not_found(self):
        with self.settings(
            GOUV_ADDRESS_SEARCH_API_DISABLED=False,
            GOUV_ADDRESS_SEARCH_API_BASE_URL=(
                f"{self.live_server_url}{reverse('test_address_api_no_result')}"
            ),
        ):
            with self.modify_settings(
                CSP_CONNECT_SRC={
                    "append": (
                        f"{self.live_server_url}{reverse('test_address_api_no_result')}"
                    )
                },
                CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
            ):
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
                    self.selenium.find_element(
                        By.CSS_SELECTOR, f"#manager-subform #id_{item}"
                    ).send_keys(value)

                Select(
                    self.selenium.find_element(By.ID, "id_is_aidant")
                ).select_by_visible_text("Oui")

                self.selenium.find_element(
                    By.CSS_SELECTOR,
                    '#id_conseiller_numerique [value="False"]',
                ).click()

                # Open dropdown
                self.selenium.find_element(
                    By.CSS_SELECTOR, "#manager-subform #id_address"
                ).click()

                self.assertEqual(
                    f"Aucun résultat trouvé pour la requête « {address} »",
                    self.selenium.find_element(By.CSS_SELECTOR, ".no-result").text,
                )

                self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

                self.wait.until(
                    self.path_matches(
                        "habilitation_new_aidants",
                        kwargs={
                            "issuer_id": str(organisation.issuer.issuer_id),
                            "uuid": str(organisation.uuid),
                        },
                    ),
                )

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
                "habilitation_new_referent",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )


@tag("functional")
class ReferentRequestFormViewNoJSTests(FunctionalTestCase):
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
            By.XPATH, f"//*[contains(text(),'{selected_address}')]"
        ).click()

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
                "habilitation_new_referent",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )


@tag("functional")
class PersonnelRequestFormViewTests(FunctionalTestCase):
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

        for i, _ in enumerate(form_elts):
            form = AidantRequestFormLegacy(
                organisation=organisation,
                prefix=f"form-{i}",
            )

            for bf in form:
                for widget in bf.subwidgets:
                    try:
                        field_label = self.selenium.find_element(
                            By.CSS_SELECTOR, f'[for="{widget.id_for_label}"]'
                        )
                    except NoSuchElementException:
                        self.fail(
                            f"Label for form element {widget.id_for_label} not found. "
                            "Was form 'prefix' or 'auto_id' modified?"
                        )

                    self.assertIn(
                        widget.data.get("label", bf.label),
                        field_label.get_attribute("innerHTML"),
                    )

    def test_form_submit_no_aidants(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        self._open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

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

        for i in range(2, 6):
            aidant_form: AidantRequestFormLegacy = get_form(
                AidantRequestFormLegacy, form_init_kwargs={"organisation": organisation}
            )
            aidant_data = aidant_form.cleaned_data
            for field_name in aidant_form.fields:
                element: WebElement = self.selenium.find_element(
                    By.CSS_SELECTOR,
                    f"#id_form-{i}-{field_name}",
                )

                if field_name == "conseiller_numerique":
                    element.find_element(
                        By.CSS_SELECTOR,
                        f'[value="{aidant_data["conseiller_numerique"]}"]',
                    ).click()
                else:
                    element.clear()
                    element.send_keys(aidant_data[field_name])

            self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

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

        modified_aidant_idx = 2
        modified_aidant_email = self.selenium.find_element(
            By.CSS_SELECTOR, f"#id_form-{modified_aidant_idx}-email"
        ).get_attribute("value")

        new_aidant_form: AidantRequestFormLegacy = get_form(
            AidantRequestFormLegacy, form_init_kwargs={"organisation": organisation}
        )
        aidant_data = new_aidant_form.cleaned_data
        for field_name in new_aidant_form.fields:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#id_form-{modified_aidant_idx}-{field_name}",
            )

            if field_name == "conseiller_numerique":
                element.find_element(
                    By.CSS_SELECTOR,
                    f'[value="{aidant_data["conseiller_numerique"]}"]',
                ).click()
            else:
                element.clear()
                element.send_keys(aidant_data[field_name])

        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

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
        self.assertEqual(organisation.aidant_requests.count(), 4)

        with self.assertRaises(AidantRequest.DoesNotExist):
            AidantRequest.objects.get(email=modified_aidant_email)

        saved_aidant = organisation.aidant_requests.get(email=aidant_data["email"])
        for field_name in new_aidant_form.fields:
            self.assertEqual(getattr(saved_aidant, field_name), aidant_data[field_name])

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

        self.selenium.find_element(By.CSS_SELECTOR, '[data-test="validate"]').click()

        error_element = self.selenium.find_element(
            By.CSS_SELECTOR, ".aidant-forms p.errorlist"
        )

        self.assertEqual(
            error_element.text,
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
