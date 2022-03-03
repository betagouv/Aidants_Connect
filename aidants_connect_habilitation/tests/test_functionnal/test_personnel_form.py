from django.test import tag
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.forms import AidantRequestForm, PersonnelForm
from aidants_connect_habilitation.models import Issuer, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    DraftOrganisationRequestFactory,
    IssuerFactory,
)


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

        for i in range(0, 5):
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
