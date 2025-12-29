import time

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.forms import (
    HabilitationRequestCreationFormSet,
    NewHabilitationRequestForm,
)
from aidants_connect_web.models import Aidant, HabilitationRequest
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


@tag("functional")
class RemoveAidantFromOrganisationTests(FunctionalTestCase):
    def setUp(self):
        self.organisation = OrganisationFactory()
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )

        self.aidant_coresponsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__is_organisation_manager=True,
        )

        self.aidant_active_with_card = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=False,
        )

        self.aidant_active_with_card_confirmed = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
        )

        self.aidant_active_without_card = AidantFactory(organisation=self.organisation)

        self.aidant_inactive_with_card = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=False,
            is_active=False,
        )

        self.aidant_inactive_with_card_confirmed = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
            is_active=False,
        )

        self.aidant_inactive_without_card = AidantFactory(
            organisation=self.organisation,
            is_active=False,
        )

        self.aidant_with_multiple_orgs = AidantFactory(organisation=self.organisation)
        self.aidant_with_multiple_orgs.organisations.add(
            OrganisationFactory(),
            OrganisationFactory(),
        )

    def test_aidants_actions(self):
        self.open_live_url(reverse("espace_responsable_organisation"))

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_responsable_organisation"))

        # Can't add or validate card for inactive aidant with card; can remove card
        self.open_live_url(
            reverse(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_inactive_with_card.id},
            )
        )
        self.assertElementNotFound(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_inactive_with_card.pk}"
        )
        self.assertElementNotFound(
            By.ID, f"validate-totp-card-for-aidant-{self.aidant_inactive_with_card.pk}"
        )
        self.selenium.find_element(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_inactive_with_card.pk}"
        )

        # Can't add or validate card or remove card for inactive aidant without card
        # Add button is displayed disabled in this case
        self.open_live_url(
            reverse(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_inactive_without_card.id},
            )
        )
        deactivated_add_button = self.selenium.find_element(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_inactive_without_card.pk}"
        )
        self.assertEqual(None, deactivated_add_button.get_attribute("href"))
        self.assertElementNotFound(
            By.ID,
            f"validate-totp-card-for-aidant-{self.aidant_inactive_without_card.pk}",
        )
        self.assertElementNotFound(
            By.ID,
            f"remove-totp-card-from-aidant-{self.aidant_inactive_without_card.pk}",
        )

        # Can unlink card for inactive aidant inactive with confirmed card
        # # Can't add or verify
        self.open_live_url(
            reverse(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_inactive_with_card_confirmed.id},
            )
        )
        self.assertElementNotFound(
            By.ID,
            f"add-totp-card-to-aidant-{self.aidant_inactive_with_card_confirmed.pk}",
        )
        self.assertElementNotFound(
            By.ID,
            "validate-totp-card-for-aidant-"
            f"{self.aidant_inactive_with_card_confirmed.pk}",
        )
        self.selenium.find_element(
            By.ID,
            "remove-totp-card-from-aidant-"
            f"{self.aidant_inactive_with_card_confirmed.pk}",
        )

        # Can add card for active aidants without card, can't remove or validate
        self.open_live_url(
            reverse(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_active_without_card.id},
            )
        )
        self.selenium.find_element(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_active_without_card.pk}"
        )
        self.assertElementNotFound(
            By.ID,
            f"validate-totp-card-for-aidant-{self.aidant_active_without_card.pk}",
        )
        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_without_card.pk}"
        )

        # Can verify and remove card for aidants with unconfirmed card, can't add
        self.open_live_url(
            reverse(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_active_with_card.id},
            )
        )
        self.assertElementNotFound(
            By.ID, f"add-totp-card-to-aidant-{self.aidant_active_with_card.pk}"
        )
        self.selenium.find_element(
            By.ID,
            f"validate-totp-card-for-aidant-{self.aidant_active_with_card.pk}",
        )
        self.selenium.find_element(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_with_card.pk}"
        )

        # Can unlink card for aidants with confirmed card, can't add or validate
        self.open_live_url(
            reverse(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_active_with_card_confirmed.id},
            )
        )
        self.assertElementNotFound(
            By.ID,
            f"add-totp-card-to-aidant-{self.aidant_active_with_card_confirmed.pk}",
        )
        self.assertElementNotFound(
            By.ID,
            "validate-totp-card-for-aidant-"
            f"{self.aidant_active_with_card_confirmed.pk}",
        )
        self.selenium.find_element(
            By.ID,
            f"remove-totp-card-from-aidant-{self.aidant_active_with_card_confirmed.pk}",
        )


@tag("functional")
class RestrictDemarchesTests(FunctionalTestCase):
    def setUp(self):
        self.organisation = OrganisationFactory(allowed_demarches=[])
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )

    def test_restrict_demarches(self):
        root_path = reverse("espace_responsable_organisation")
        selected = ["papiers", "logement"]

        self.open_live_url(root_path)

        self.assertEqual([], self.organisation.allowed_demarches)
        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_responsable_organisation"))
        for demarche in selected:
            self.selenium.find_element(
                By.CSS_SELECTOR, f'[for="id_demarches_{demarche}"]'
            ).click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait.until(self.path_matches("espace_responsable_organisation"))

        self.organisation.refresh_from_db()
        self.assertEqual(selected, self.organisation.allowed_demarches)

    def test_select_no_demarche_raises_error(self):
        self.open_live_url(reverse("espace_responsable_organisation"))

        self.assertEqual([], self.organisation.allowed_demarches)
        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_responsable_organisation"))

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait.until(self.path_matches("espace_responsable_organisation"))
        self.assertEqual(
            "Vous devez sélectionner au moins une démarche.",
            self.selenium.find_element(By.CSS_SELECTOR, ".notification.error").text,
        )


@tag("functional")
class NewHabilitationRequestTests(FunctionalTestCase):
    def setUp(self):
        self.organisation = OrganisationFactory(allowed_demarches=[], with_aidants=True)
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )

        self.path = reverse("espace_responsable_aidant_new")
        self.empty_form = NewHabilitationRequestForm(
            form_kwargs={
                "habilitation_requests": {
                    "form_kwargs": {"referent": self.aidant_responsable}
                }
            }
        )

    def test_submit_form_errors(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)

        # First form is empty
        self.wait.until(self.dsfr_ready())

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.ID, "partial-submit").click()

        self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, ".errorlist .fr-error-text")
            )
        )

        # Wait for the expected number of error messages to be fully loaded
        expected = (
            # We ignore course type error in JS mode since we're only checking
            # the profile form
            len(self._all_visible_fields())
            - len(
                [
                    f
                    for f in self._course_type_form.visible_fields()
                    if f.name != "email_formateur"
                ]
            )
        )

        self.wait.until(
            lambda driver: len(
                [
                    error
                    for error in driver.find_elements(By.CLASS_NAME, "errorlist")
                    if error.text.strip() and "Ce champ est obligatoire." in error.text
                ]
            )
            >= expected
        )

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        # Filter out empty errors for the assertion
        non_empty_errors = [error for error in errors if error.text.strip()]
        self.assertEqual(expected, len(non_empty_errors))

        for error in non_empty_errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # First form is not empty but not filled either
        self.open_live_url(self.path)
        self.wait.until(self.dsfr_ready())

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.CSS_SELECTOR, '[id$="email"]').send_keys(
            "test@test.test"
        )
        self.selenium.find_element(By.ID, "partial-submit").click()

        with self.implicitely_wait(0):
            self.wait.until(
                expected_conditions.presence_of_element_located(
                    (By.CLASS_NAME, "errorlist")
                )
            )

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        expected = (
            # We ignore course type error in JS mode since we're only checking
            # the profile form
            len(self._all_visible_fields())
            - len(
                [
                    f
                    for f in self._course_type_form.visible_fields()
                    if f.name != "email_formateur"
                ]
            )
            - 1
        )
        # Filter out empty errors for the assertion
        non_empty_errors = [error for error in errors if error.text.strip()]
        self.assertEqual(expected, len(non_empty_errors))

        for error in non_empty_errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # ----------------------------------------------------------------------------
        # Testing submit for button
        # ----------------------------------------------------------------------------

        # First form is not empty but not filled either
        self.open_live_url(self.path)
        self.wait.until(self.dsfr_ready())

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.ID, "form-submit").click()

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        # Filter out empty errors for the assertion
        non_empty_errors = [error for error in errors if error.text.strip()]
        self.assertEqual(len(self._all_visible_fields()), len(non_empty_errors))

        for error in non_empty_errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # First form is not empty but not filled either
        self.open_live_url(self.path)
        self.selenium.find_element(By.CSS_SELECTOR, '[id$="email"]').send_keys(
            "test@test.test"
        )

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.ID, "form-submit").click()
        self.wait.until(self.document_loaded())

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        # Filter out empty errors for the assertion
        non_empty_errors = [error for error in errors if error.text.strip()]
        self.assertEqual(len(self._all_visible_fields()) - 1, len(non_empty_errors))

        for error in non_empty_errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # ----------------------------------------------------------------------------
        # Asserting not new habilitation was created
        # ----------------------------------------------------------------------------
        self.assertFalse(HabilitationRequest.objects.count())

    def test_submitting_request(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())

        # Wait for email field to be visible before filling
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, "id_multiform-habilitation_requests-0-email")
            )
        )

        req: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req, self._all_visible_fields(), self._custom_getter)
        self.selenium.find_element(By.ID, "form-submit").click()
        hab: HabilitationRequest = HabilitationRequest.objects.first()
        self.assertEqual(
            {
                req.get_full_name(),
                req.email,
                req.profession,
                req.conseiller_numerique,
                req.organisation,
            },
            {
                hab.get_full_name(),
                hab.email,
                hab.profession,
                hab.conseiller_numerique,
                hab.organisation,
            },
        )

    def test_adding_profile_then_submitting_empty(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())
        req: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req, self._all_visible_fields(), self._custom_getter)
        self.selenium.find_element(By.ID, "partial-submit").click()

        # Check accordion title shows user info
        accordion_title = self.selenium.find_element(
            By.CSS_SELECTOR, ".fr-accordion__btn .fr-text--lg.fr-text--bold"
        )
        self.assertNormalizedStringEqual(
            req.get_full_name(),
            accordion_title.text,
        )

        # open the accordion
        self.js_click(By.CSS_SELECTOR, ".fr-accordion__btn")

        # Check form fields contain the expected values
        email_field = self.selenium.find_element(By.CSS_SELECTOR, 'input[id$="email"]')
        self.assertEqual(req.email, email_field.get_attribute("value"))

        profession_field = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[id$="profession"]'
        )
        self.assertEqual(req.profession, profession_field.get_attribute("value"))
        # Asserting no new habilitation was created
        self.assertFalse(HabilitationRequest.objects.count())
        # Now submits the form
        self.selenium.find_element(By.ID, "form-submit").click()
        hab: HabilitationRequest = HabilitationRequest.objects.first()
        self.assertEqual(
            {
                req.get_full_name(),
                req.email,
                req.profession,
                req.conseiller_numerique,
                req.organisation,
            },
            {
                hab.get_full_name(),
                hab.email,
                hab.profession,
                hab.conseiller_numerique,
                hab.organisation,
            },
        )

    def test_adding_profile_then_submitting_filled_form(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())

        # Wait for email field to be visible before filling
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, "id_multiform-habilitation_requests-0-email")
            )
        )

        req1: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req1, self._all_visible_fields(), self._custom_getter)

        # Scroll and click partial submit
        partial_submit_btn = self.selenium.find_element(By.ID, "partial-submit")
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            partial_submit_btn,
        )
        time.sleep(0.1)
        partial_submit_btn.click()

        # Check accordion title shows user info
        accordion_title = self.selenium.find_element(
            By.CSS_SELECTOR, ".fr-accordion__btn .fr-text--lg.fr-text--bold"
        )
        self.assertNormalizedStringEqual(
            req1.get_full_name(),
            accordion_title.text,
        )

        # open the accordion
        self.js_click(By.CSS_SELECTOR, ".fr-accordion__btn")

        # Check form fields contain the expected values
        email_field = self.selenium.find_element(By.CSS_SELECTOR, 'input[id$="email"]')
        self.assertEqual(req1.email, email_field.get_attribute("value"))

        profession_field = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[id$="profession"]'
        )
        self.assertEqual(req1.profession, profession_field.get_attribute("value"))
        # Asserting not new habilitation was created
        self.assertFalse(HabilitationRequest.objects.count())

        # Click "Ajouter un autre aidant" to add a second form
        self.selenium.find_element(By.ID, "partial-submit").click()
        self.wait.until(self.document_loaded())

        req2: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )

        # Wait for second form email field to be visible before filling
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, "id_multiform-habilitation_requests-1-email")
            )
        )

        self.fill_form(req2, self._all_visible_fields(1), self._custom_getter)

        # Now submits the form
        self.selenium.find_element(By.ID, "form-submit").click()
        self.assertEqual(
            set(
                HabilitationRequest.objects.values_list(
                    "first_name",
                    "last_name",
                    "email",
                    "profession",
                    "conseiller_numerique",
                    "organisation",
                ).all()
            ),
            {
                (
                    req1.first_name,
                    req1.last_name,
                    req1.email,
                    req1.profession,
                    req1.conseiller_numerique,
                    req1.organisation.pk,
                ),
                (
                    req2.first_name,
                    req2.last_name,
                    req2.email,
                    req2.profession,
                    req2.conseiller_numerique,
                    req2.organisation.pk,
                ),
            },
        )

    def test_duplicate_email_error(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())

        # Add first aidant
        req1 = HabilitationRequestFactory.build(organisation=self.organisation)

        # Wait for email field to be visible before filling
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, "id_multiform-habilitation_requests-0-email")
            )
        )

        self.fill_form(req1, self._all_visible_fields(0), self._custom_getter)

        # Scroll and click partial submit
        partial_submit_btn = self.selenium.find_element(By.ID, "partial-submit")
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            partial_submit_btn,
        )
        time.sleep(0.1)
        partial_submit_btn.click()
        self.wait.until(self.document_loaded())

        # Wait for second accordion to appear
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, "id_multiform-habilitation_requests-1-email")
            )
        )

        # Add second aidant with same email
        req2 = HabilitationRequestFactory.build(organisation=self.organisation)
        req2.email = req1.email  # Same email to trigger error
        self.fill_form(req2, self._all_visible_fields(1), self._custom_getter)

        # Scroll and click partial submit again
        partial_submit_btn = self.selenium.find_element(By.ID, "partial-submit")
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            partial_submit_btn,
        )
        time.sleep(0.1)
        partial_submit_btn.click()

        # Wait for page to load and check for duplicate errors in email fields
        self.wait.until(self.document_loaded())

        # Check for errors in email fields
        error_elements = self.selenium.find_elements(
            By.CSS_SELECTOR, '[id$="email-desc-error"] .errorlist'
        )

        self.assertGreater(len(error_elements), 0, "No email validation errors found")

        # Check that error message contains the duplicate email
        error_found = False
        for error_element in error_elements:
            error_text = error_element.text
            if "apparaît plusieurs fois" in error_text:
                error_found = True
                self.assertIn(
                    "Chaque aidant doit avoir son propre e-mail nominatif", error_text
                )
                self.assertIn(req1.email, error_text)
                break

        self.assertTrue(error_found, "Expected duplicate email error message not found")

        # We should have 2 accordions (first + second with error), not 3
        accordions = self.selenium.find_elements(By.CSS_SELECTOR, ".fr-accordion")
        self.assertEqual(
            2,
            len(accordions),
            "Third aidant should not be added due to duplicate email error",
        )

        # Verify no requests were created in database due to validation errors
        self.assertEqual(0, HabilitationRequest.objects.count())

    @property
    def _habilitation_requests_form(self) -> HabilitationRequestCreationFormSet:
        return self.empty_form["habilitation_requests"]

    @property
    def _course_type_form(self):
        return self.empty_form["course_type"]

    def _all_visible_fields(self, form_idx=0):
        form = self._habilitation_requests_form._construct_form(
            form_idx, **self._habilitation_requests_form.get_form_kwargs(form_idx)
        )
        course_fields = [
            f
            for f in self._course_type_form.visible_fields()
            if f.name != "email_formateur"
        ]
        return [*form.visible_fields(), *course_fields]

    @staticmethod
    def _custom_getter(data, field, default_getter):
        return (
            default_getter(data, "course_type")
            if field == "type"
            else default_getter(data, field)
        )
