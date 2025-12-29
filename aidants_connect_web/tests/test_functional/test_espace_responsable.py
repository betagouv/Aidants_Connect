import itertools
from unittest import skip

from django.template.defaultfilters import yesno
from django.test import tag
from django.urls import reverse

from faker import Faker
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

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        expected = (
            # We ignore course type error in JS mode since we're only checking
            # the profile form
            len(self._all_visible_fields())
            - len(self._course_type_form.visible_fields())
        )
        self.assertEqual(expected, len(errors))

        for error in errors:
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
            - len(self._course_type_form.visible_fields())
            - 1
        )
        self.assertEqual(expected, len(errors))

        for error in errors:
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
        self.assertEqual(len(self._all_visible_fields()), len(errors))

        for error in errors:
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
        self.assertEqual(len(self._all_visible_fields()) - 1, len(errors))

        for error in errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # ----------------------------------------------------------------------------
        # Asserting not new habilitation was created
        # ----------------------------------------------------------------------------
        self.assertFalse(HabilitationRequest.objects.count())

    def test_submitting_request(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())
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

        self.assertNormalizedStringEqual(
            f"{req.get_full_name()} {req.email}",
            self.selenium.find_element(By.CSS_SELECTOR, "#added-form-0 summary").text,
        )

        # open the <details>
        self.js_click(By.CSS_SELECTOR, "#added-form-0 summary")
        self.assertNormalizedStringEqual(
            " ".join(
                [
                    f"Email {req.email}",
                    f"Profession {req.profession}",
                    "Conseiller numérique",
                    f"{yesno(req.conseiller_numerique, 'Oui,Non')}",
                    f"Organisation {req.organisation}",
                ]
            ),
            self.selenium.find_element(
                By.CSS_SELECTOR, "#added-form-0 .user-informations"
            ).text,
        )
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
        req1: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req1, self._all_visible_fields(), self._custom_getter)

        self.selenium.find_element(By.ID, "partial-submit").click()

        self.assertNormalizedStringEqual(
            f"{req1.get_full_name()} {req1.email}",
            self.selenium.find_element(By.CSS_SELECTOR, "#added-form-0 summary").text,
        )

        # open the <details>
        self.js_click(By.CSS_SELECTOR, "#added-form-0 summary")
        self.assertNormalizedStringEqual(
            " ".join(
                [
                    f"Email {req1.email}",
                    f"Profession {req1.profession}",
                    "Conseiller numérique",
                    f"{yesno(req1.conseiller_numerique, 'Oui,Non')}",
                    f"Organisation {req1.organisation}",
                ]
            ),
            self.selenium.find_element(
                By.CSS_SELECTOR, "#added-form-0 .user-informations"
            ).text,
        )
        # Asserting not new habilitation was created
        self.assertFalse(HabilitationRequest.objects.count())

        req2: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
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

    def test_editing_profile_checks_errors(self):
        idx_to_modify = 1

        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())

        existing_req = HabilitationRequestFactory(organisation=self.organisation)

        reqs = [
            HabilitationRequestFactory.build(organisation=self.organisation)
            for _ in range(3)
        ]
        for i, req in enumerate(reqs):
            self.fill_form(req, self._all_visible_fields(i), self._custom_getter)
            self.selenium.find_element(By.ID, "partial-submit").click()
            self.assertEqual(
                "Ajouter un autre aidant",
                self.selenium.find_element(By.ID, "partial-submit").text,
            )

        self._try_open_modal(By.ID, "edit-button-1")

        # Submit checks
        self.selenium.find_element(
            By.CSS_SELECTOR, '[data-test="edited-form"] input[id$="email"]'
        ).clear()

        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-submit"
        ).click()

        self.assertNormalizedStringEqual(
            "Ce champ est obligatoire.",
            self.selenium.find_element(
                By.CSS_SELECTOR,
                '[data-test="edited-form"] [id$="email-desc-error"] .errorlist',
            ).text,
        )

        # Test conflict with another profile in this request
        elt = self.selenium.find_element(
            By.CSS_SELECTOR, '[data-test="edited-form"] input[id$="email"]'
        )
        elt.clear()
        elt.send_keys(reqs[idx_to_modify + 1].email)
        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-submit"
        ).click()
        self.assertNormalizedStringEqual(
            "Corrigez les données en double dans email et "
            "organisation qui doit contenir des valeurs uniques.",
            self.selenium.find_element(By.CSS_SELECTOR, ".errorlist.nonform").text,
        )

        # Test conflict with existing request
        elt = self.selenium.find_element(
            By.CSS_SELECTOR, '[data-test="edited-form"] input[id$="email"]'
        )
        elt.clear()
        elt.send_keys(existing_req.email)
        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-submit"
        ).click()
        self.assertNormalizedStringEqual(
            "Erreur : une demande d’habilitation est déjà en cours pour "
            "l’adresse e-mail. Vous n’avez pas besoin de déposer une nouvelle "
            "demande pour cette adresse-ci.",
            self.selenium.find_element(
                By.CSS_SELECTOR,
                '[data-test="edited-form"] [id$="email-desc-error"] .errorlist',
            ).text,
        )

        for _ in range(10):
            if (
                new_email := Faker().email()
            ) not in HabilitationRequest.objects.all().values_list("email", flat=True):
                break
        else:
            self.fail("Coundl't generate a new email")

        elt = self.selenium.find_element(
            By.CSS_SELECTOR, '[data-test="edited-form"] input[id$="email"]'
        )
        elt.clear()
        elt.send_keys(new_email)

        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-submit"
        ).click()
        self.wait.until(self._modal_closed())
        self.selenium.find_element(By.ID, "form-submit").click()
        self.wait.until(self.path_matches("espace_responsable_aidants"))

        # Don't forget to modify the data for the test
        reqs[idx_to_modify].email = new_email

        self.assertEqual(4, len(HabilitationRequest.objects.all()))
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
                    req.first_name,
                    req.last_name,
                    req.email,
                    req.profession,
                    req.conseiller_numerique,
                    req.organisation.pk,
                )
                for req in itertools.chain([existing_req], reqs)
            },
        )

    @skip("will be deleted in new add aidant form")
    def test_prevents_form_erase_when_editing(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.dsfr_ready())
        req1: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req1, self._all_visible_fields(), self._custom_getter)
        self.selenium.find_element(By.ID, "partial-submit").click()

        # Attendre que le DOM soit stable après le clic et re-trouver l'élément
        self.wait.until(self.document_loaded())
        email_input = self.selenium.find_element(
            By.CSS_SELECTOR, '#empty-form input[id$="email"]'
        )
        email_input.send_keys(req1.email)

        self._try_open_modal(By.ID, "edit-button-0")

        actual = self.selenium.execute_script(
            "return arguments[0].value",
            self.selenium.find_element(
                By.CSS_SELECTOR, '#empty-form input[id$="email"]'
            ),
        )

        self.assertEqual(
            req1.email,
            actual,
            "Editing form is not correctly filled. "
            f"Expected email field to be {req1.email}, was {actual}",
        )

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
        return [
            *form.visible_fields(),
            *self._course_type_form.visible_fields(),
        ]

    @staticmethod
    def _custom_getter(data, field, default_getter):
        return (
            default_getter(data, "course_type")
            if field == "type"
            else default_getter(data, field)
        )

    def _modal_closed(self):
        def modal_has_no_open_attr(driver):
            try:
                with self.implicitely_wait(0, driver):
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

    def _try_close_modal(self):
        self.wait.until(self.document_loaded())
        self.wait.until(self.dsfr_ready())
        with self.implicitely_wait(0.1):
            self.wait.until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "#main-modal")
                ),
                "Modal didn't seem to have been initialized",
            )

            self.js_click(By.TAG_NAME, "body")

            self.wait.until(self._modal_closed(), "Modal seems to be still visible")

    def _try_open_modal(self, by, value: str):
        self._try_close_modal()
        self.js_click(by, value)
        with self.implicitely_wait(0.1):
            self.wait.until(
                expected_conditions.text_to_be_present_in_element_attribute(
                    (By.CSS_SELECTOR, "#main-modal"), "open", "true"
                ),
                "Modal was not opened",
            )

            self.wait.until(
                expected_conditions.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        '#main-modal input[id$="-email"]',
                    )
                ),
                "Modal seems opened but form seems not visible",
            )
