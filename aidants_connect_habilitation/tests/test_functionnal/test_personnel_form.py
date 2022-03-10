from django.test import tag
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.forms import (
    AidantRequestForm,
    DataPrivacyOfficerForm,
    ManagerForm,
    PersonnelForm,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    DataPrivacyOfficer,
    Issuer,
    Manager,
    OrganisationRequest,
)
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    DataPrivacyOfficerFactory,
    DraftOrganisationRequestFactory,
    IssuerFactory,
    ManagerFactory,
)
from aidants_connect_habilitation.tests.utils import get_form


@tag("functional")
class PersonnelRequestFormViewTests(FunctionalTestCase):
    def test_js_managment_form_aidant_count_is_modified(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer
        )
        self.__open_form_url(issuer, organisation)

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
        self.__open_form_url(issuer, organisation)

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
        self.__open_form_url(issuer, organisation)

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

        self.__open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()
        self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()

        form_elts = self.selenium.find_elements(
            By.CSS_SELECTOR, ".aidant-form-container"
        )

        self.assertEqual(len(form_elts), 4)

        form = AidantRequestForm()

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
        manager: Manager = ManagerFactory()
        form = ManagerForm()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer, manager=manager
        )

        self.__open_form_url(issuer, organisation)

        field_names = list(form.fields.keys())
        field_names.remove("is_aidant")

        element: WebElement = self.selenium.find_element(
            By.CSS_SELECTOR,
            f"#id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant",
        )
        if manager.is_aidant:
            self.assertIsNotNone(element.get_attribute("checked"), "")
        else:
            self.assertIsNone(element.get_attribute("checked"))

        for field_name in field_names:
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#id_{PersonnelForm.MANAGER_FORM_PREFIX}-{field_name}",
            )

            self.assertEqual(
                element.get_attribute("value"), getattr(manager, field_name)
            )

        pass

    def test_form_modify_manager_data(self):
        issuer: Issuer = IssuerFactory()
        manager: Manager = ManagerFactory()
        form = ManagerForm()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
            data_privacy_officer=DataPrivacyOfficerFactory(),
        )

        self.__open_form_url(issuer, organisation)

        new_manager: Manager = ManagerFactory.build()

        field_name = list(form.fields.keys())
        field_name.remove("is_aidant")

        if new_manager.is_aidant:
            self.selenium.execute_script(
                f"""document.querySelector("#id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant")"""  # noqa
                """.setAttribute("checked", "checked")"""
            )
        else:
            self.selenium.execute_script(
                f"""document.querySelector("#id_{PersonnelForm.MANAGER_FORM_PREFIX}-is_aidant")"""  # noqa
                """.removeAttribute("checked")"""
            )

        for field_name in field_name:
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
                "draft_id": str(organisation.draft_id),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        saved_manager = organisation.manager

        for field_name in form.fields:
            self.assertEqual(
                getattr(saved_manager, field_name), getattr(new_manager, field_name)
            )

    def test_form_modify_dpo_data(self):
        issuer: Issuer = IssuerFactory()
        dpo: DataPrivacyOfficer = DataPrivacyOfficerFactory()
        form = DataPrivacyOfficerForm()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=ManagerFactory(),
            data_privacy_officer=dpo,
        )

        self.__open_form_url(issuer, organisation)

        new_dpo: Manager = DataPrivacyOfficerFactory.build()

        for field_name in list(form.fields.keys()):
            element: WebElement = self.selenium.find_element(
                By.CSS_SELECTOR,
                f"#id_{PersonnelForm.DPO_FORM_PREFIX}-{field_name}",
            )
            element.clear()
            element.send_keys(str(getattr(new_dpo, field_name)))

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "draft_id": str(organisation.draft_id),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        saved_dpo = organisation.data_privacy_officer

        for field_name in form.fields:
            self.assertEqual(
                getattr(saved_dpo, field_name), getattr(new_dpo, field_name)
            )

    def test_form_submit_no_aidants(self):
        issuer: Issuer = IssuerFactory()
        dpo: DataPrivacyOfficer = DataPrivacyOfficerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
            data_privacy_officer=dpo,
        )

        self.__open_form_url(issuer, organisation)

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "draft_id": str(organisation.draft_id),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 0)

    def test_form_submit_multiple_aidants(self):
        issuer: Issuer = IssuerFactory()
        dpo: DataPrivacyOfficer = DataPrivacyOfficerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
            data_privacy_officer=dpo,
        )

        # Setup 2 initial requests
        AidantRequestFactory(organisation=organisation)
        AidantRequestFactory(organisation=organisation)

        self.__open_form_url(issuer, organisation)

        for i in range(2, 6):
            aidant_form: AidantRequestForm = get_form(AidantRequestForm)
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
                "draft_id": str(organisation.draft_id),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 6)

    def test_form_submit_modify_multiple_aidants(self):
        issuer: Issuer = IssuerFactory()
        dpo: DataPrivacyOfficer = DataPrivacyOfficerFactory()
        manager: Manager = ManagerFactory()
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=issuer,
            manager=manager,
            data_privacy_officer=dpo,
        )

        AidantRequestFactory(organisation=organisation)
        AidantRequestFactory(organisation=organisation)
        AidantRequestFactory(organisation=organisation)
        AidantRequestFactory(organisation=organisation)

        self.__open_form_url(issuer, organisation)

        modified_aidant_idx = 2
        modified_aidant_email = self.selenium.find_element(
            By.CSS_SELECTOR,
            f"#id_{PersonnelForm.AIDANTS_FORMSET_PREFIX}-{modified_aidant_idx}-email",
        ).get_attribute("value")

        new_aidant_form: AidantRequestForm = get_form(AidantRequestForm)
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
                "draft_id": str(organisation.draft_id),
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

    def __open_form_url(
        self,
        issuer: Issuer,
        organisation_request: OrganisationRequest,
    ):
        self.open_live_url(
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "draft_id": organisation_request.draft_id,
                },
            )
        )
