from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.constants import AddAidantProfileChoice
from aidants_connect_web.models import Aidant, HabilitationRequest
from aidants_connect_web.models.other_models import StructureChangeRequest
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


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
        self.open_live_url(reverse("espace_referent:organisation"))

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_referent:organisation"))

        # Can't add or validate card for inactive aidant with card; can remove card
        self.open_live_url(
            reverse(
                "espace_referent:choose_totp",
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
                "espace_referent:choose_totp",
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
                "espace_referent:choose_totp",
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
                "espace_referent:choose_totp",
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
                "espace_referent:choose_totp",
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
                "espace_referent:choose_totp",
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
        root_path = reverse("espace_referent:organisation")
        selected = ["papiers", "logement"]

        self.open_live_url(root_path)

        self.assertEqual([], self.organisation.allowed_demarches)
        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_referent:organisation"))
        for demarche in selected:
            self.selenium.find_element(
                By.CSS_SELECTOR, f'[for="id_demarches_{demarche}"]'
            ).click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait.until(self.path_matches("espace_referent:organisation"))

        self.organisation.refresh_from_db()
        self.assertEqual(selected, self.organisation.allowed_demarches)

    def test_select_no_demarche_raises_error(self):
        self.open_live_url(reverse("espace_referent:organisation"))

        self.assertEqual([], self.organisation.allowed_demarches)
        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_referent:organisation"))

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait.until(self.path_matches("espace_referent:organisation"))
        self.assertEqual(
            "Vous devez sélectionner au moins une démarche.",
            self.selenium.find_element(By.CSS_SELECTOR, ".notification.error").text,
        )


@tag("functional")
class NewHabilitationRequestTests(FunctionalTestCase):
    def setUp(self):
        self.organisation = OrganisationFactory(allowed_demarches=[])
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )
        self.other_org = OrganisationFactory(name="Autre structure")
        self.trained_aidant = AidantFactory(organisation=self.other_org)

        self.step1_url = reverse("espace_referent:aidant_new_profile")

    # ── helpers ──────────────────────────────────────────────────────────

    def _login_and_go_to_step1(self):
        self.open_live_url(self.step1_url)
        self.login_aidant(self.aidant_responsable)
        self.wait.until(self.path_matches("espace_referent:aidant_new_profile"))

    def _choose_profile(self, choice):
        radio_idx = choice - 1
        self.js_click(By.ID, f"id_profile_{radio_idx}")
        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

    def _select_course_type_classic(self):
        self.js_click(By.ID, "id_multiform-course_type-type_0")

    def _fill_untrained_aidant(self, idx, email, first_name, last_name, profession):
        prefix = f"id_multiform-habilitation_requests-{idx}"
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, f"{prefix}-email")
            )
        )
        for field_name, value in [
            ("email", email),
            ("first_name", first_name),
            ("last_name", last_name),
            ("profession", profession),
        ]:
            elt = self.selenium.find_element(By.ID, f"{prefix}-{field_name}")
            elt.clear()
            elt.send_keys(value)
        Select(
            self.selenium.find_element(By.ID, f"{prefix}-organisation")
        ).select_by_value(str(self.organisation.pk))
        self.js_click(By.ID, f"{prefix}-conseiller_numerique_1")

    def _fill_trained_aidant_email(self, idx, email):
        prefix = f"id_form-{idx}"
        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, f"{prefix}-email")
            )
        )
        elt = self.selenium.find_element(By.ID, f"{prefix}-email")
        elt.clear()
        elt.send_keys(email)

    def _fill_trained_aidant_email_change(
        self, idx, email_will_change=False, new_email=None
    ):
        prefix = f"id_form-{idx}"
        will_change_idx = 0 if email_will_change else 1
        self.js_click(By.ID, f"{prefix}-email_will_change_{will_change_idx}")
        if email_will_change and new_email:
            self.wait.until(
                expected_conditions.visibility_of_element_located(
                    (By.ID, f"{prefix}-new_email")
                )
            )
            new_email_elt = self.selenium.find_element(By.ID, f"{prefix}-new_email")
            new_email_elt.clear()
            new_email_elt.send_keys(new_email)

    def _submit_trained_form_next(self):
        btn = self.selenium.find_element(
            By.CSS_SELECTOR, 'button[type="submit"]:not([name])'
        )
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", btn
        )
        btn.click()

    def _confirm_wizard(self, expected_texts=None, unexpected_texts=None):
        self.wait.until(self.path_matches("espace_referent:aidant_new_confirmation"))
        if expected_texts:
            page_text = self.selenium.find_element(By.TAG_NAME, "body").text
            for text in expected_texts:
                self.assertIn(text, page_text)
        if unexpected_texts:
            page_text = self.selenium.find_element(By.TAG_NAME, "body").text
            for text in unexpected_texts:
                self.assertNotIn(text, page_text)
        self.selenium.find_element(
            By.CSS_SELECTOR, 'button[name="wizard_confirm"]'
        ).click()
        self.wait.until(self.path_matches("espace_referent:aidants"))

    def _remove_required_attributes(self):
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

    def _wait_for_errors(self):
        self.wait.until(
            lambda driver: (
                len(
                    [
                        e
                        for e in driver.find_elements(By.CLASS_NAME, "errorlist")
                        if e.text.strip()
                    ]
                )
                > 0
            )
        )
        return [
            e
            for e in self.selenium.find_elements(By.CLASS_NAME, "errorlist")
            if e.text.strip()
        ]

    # ── NOT_YET_TRAINED scenarios ───────────────────────────────────────────

    NOT_YET_TRAINED_EXPECTED = [
        "L’éligibilité des aidants sera vérifée par notre équipe",
        "inscrire les aidants en formation",
    ]
    NOT_YET_TRAINED_UNEXPECTED = [
        "vous pourrez associer un moyen de connexion aux aidants",
    ]

    ALREADY_TRAINED_EXPECTED = [
        "La demande d'ajout, pour les aidants suivants, sera vérifiée par notre équipe",
        "vous pourrez associer un moyen de connexion aux aidants",
    ]
    ALREADY_TRAINED_UNEXPECTED = [
        "L’éligibilité des aidants sera vérifée",
    ]

    def test_none_trained_single_aidant(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.NOT_YET_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_untrained"))
        self.wait.until(self.dsfr_ready())

        self._select_course_type_classic()
        self._fill_untrained_aidant(
            0, "jean@example.com", "Jean", "Dupont", "Secrétaire"
        )
        self.selenium.find_element(By.ID, "form-submit").click()

        self._confirm_wizard(
            expected_texts=self.NOT_YET_TRAINED_EXPECTED,
            unexpected_texts=self.NOT_YET_TRAINED_UNEXPECTED,
        )

        self.assertEqual(1, HabilitationRequest.objects.count())
        hab = HabilitationRequest.objects.first()
        self.assertEqual("jean@example.com", hab.email)
        self.assertEqual("Jean", hab.first_name)
        self.assertEqual("Dupont", hab.last_name)
        self.assertEqual("Secrétaire", hab.profession)
        self.assertEqual(self.organisation, hab.organisation)

    def test_none_trained_multiple_aidants_with_partial_submit(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.NOT_YET_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_untrained"))
        self.wait.until(self.dsfr_ready())

        self._select_course_type_classic()
        self._fill_untrained_aidant(
            0, "jean@example.com", "Jean", "Dupont", "Secrétaire"
        )

        partial_btn = self.selenium.find_element(By.ID, "partial-submit")
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", partial_btn
        )
        partial_btn.click()
        self.wait.until(self.document_loaded())

        accordion_title = self.selenium.find_element(
            By.CSS_SELECTOR, ".fr-accordion__btn .fr-text--lg.fr-text--bold"
        )
        self.assertNormalizedStringEqual("Jean Dupont", accordion_title.text)
        self.assertFalse(HabilitationRequest.objects.exists())

        self._fill_untrained_aidant(
            1, "marie@example.com", "Marie", "Martin", "Assistante"
        )
        self.selenium.find_element(By.ID, "form-submit").click()

        self._confirm_wizard(
            expected_texts=self.NOT_YET_TRAINED_EXPECTED,
            unexpected_texts=self.NOT_YET_TRAINED_UNEXPECTED,
        )

        self.assertEqual(2, HabilitationRequest.objects.count())
        emails = set(HabilitationRequest.objects.values_list("email", flat=True))
        self.assertEqual({"jean@example.com", "marie@example.com"}, emails)

    def test_none_trained_form_validation_errors(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.NOT_YET_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_untrained"))
        self.wait.until(self.dsfr_ready())

        self._remove_required_attributes()
        self.selenium.find_element(By.ID, "form-submit").click()
        self.wait.until(self.document_loaded())

        errors = self._wait_for_errors()
        self.assertGreater(len(errors), 0)
        self.assertTrue(
            any("Ce champ est obligatoire." in e.text for e in errors),
            "Should have required field errors",
        )
        self.assertFalse(HabilitationRequest.objects.exists())

    def test_none_trained_partial_submit_validation_errors(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.NOT_YET_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_untrained"))
        self.wait.until(self.dsfr_ready())

        self._remove_required_attributes()

        self.selenium.find_element(By.CSS_SELECTOR, '[id$="email"]').send_keys(
            "test@test.test"
        )
        self.selenium.find_element(By.ID, "partial-submit").click()

        errors = self._wait_for_errors()
        self.assertGreater(len(errors), 0)
        for error in errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        self.assertFalse(HabilitationRequest.objects.exists())

    def test_none_trained_duplicate_email_error(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.NOT_YET_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_untrained"))
        self.wait.until(self.dsfr_ready())

        self._select_course_type_classic()
        self._fill_untrained_aidant(
            0, "dup@example.com", "Jean", "Dupont", "Secrétaire"
        )

        partial_btn = self.selenium.find_element(By.ID, "partial-submit")
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", partial_btn
        )
        partial_btn.click()
        self.wait.until(self.document_loaded())

        self.wait.until(
            expected_conditions.visibility_of_element_located(
                (By.ID, "id_multiform-habilitation_requests-1-email")
            )
        )

        self._fill_untrained_aidant(
            1, "dup@example.com", "Marie", "Martin", "Assistante"
        )

        partial_btn = self.selenium.find_element(By.ID, "partial-submit")
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", partial_btn
        )
        partial_btn.click()
        self.wait.until(self.document_loaded())

        accordions = self.selenium.find_elements(By.CSS_SELECTOR, ".fr-accordion")
        self.assertEqual(
            2,
            len(accordions),
            "Third aidant should not be added due to duplicate email error",
        )
        self.assertEqual(0, HabilitationRequest.objects.count())

    # ── ALREADY_TRAINED scenarios ────────────────────────────────────────────

    def test_all_trained_single_aidant(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.ALREADY_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_trained"))
        self.wait.until(self.dsfr_ready())

        self._fill_trained_aidant_email(0, self.trained_aidant.email)
        self._submit_trained_form_next()
        self.wait.until(self.document_loaded())

        self._submit_trained_form_next()

        self._confirm_wizard(
            expected_texts=self.ALREADY_TRAINED_EXPECTED,
            unexpected_texts=self.ALREADY_TRAINED_UNEXPECTED,
        )

        self.assertEqual(1, StructureChangeRequest.objects.count())
        scr = StructureChangeRequest.objects.first()
        self.assertEqual(self.trained_aidant.email.lower(), scr.email)
        self.assertEqual(self.organisation, scr.organisation)
        self.assertFalse(scr.new_email)

    def test_all_trained_with_email_change(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.ALREADY_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_trained"))
        self.wait.until(self.dsfr_ready())

        self._fill_trained_aidant_email(0, self.trained_aidant.email)
        self._submit_trained_form_next()
        self.wait.until(self.document_loaded())

        self._fill_trained_aidant_email_change(
            0, email_will_change=True, new_email="new@example.com"
        )
        self._submit_trained_form_next()

        self._confirm_wizard(
            expected_texts=self.ALREADY_TRAINED_EXPECTED,
            unexpected_texts=self.ALREADY_TRAINED_UNEXPECTED,
        )

        self.assertEqual(1, StructureChangeRequest.objects.count())
        scr = StructureChangeRequest.objects.first()
        self.assertEqual(self.trained_aidant.email.lower(), scr.email)
        self.assertEqual("new@example.com", scr.new_email)

    def test_all_trained_invalid_email_shows_error(self):
        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.ALREADY_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_trained"))
        self.wait.until(self.dsfr_ready())

        self._fill_trained_aidant_email(0, "unknown@example.com")
        self._submit_trained_form_next()
        self.wait.until(self.document_loaded())

        errors = self._wait_for_errors()
        self.assertGreater(len(errors), 0)
        self.assertTrue(
            any("erronée" in e.text or "habilité" in e.text for e in errors)
        )
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_multiple_aidants(self):
        trained_aidant2 = AidantFactory(organisation=self.other_org)

        self._login_and_go_to_step1()
        self._choose_profile(AddAidantProfileChoice.ALREADY_TRAINED)
        self.wait.until(self.path_matches("espace_referent:aidant_new_trained"))
        self.wait.until(self.dsfr_ready())

        self._fill_trained_aidant_email(0, self.trained_aidant.email)

        add_btn = self.selenium.find_element(
            By.CSS_SELECTOR, 'button[name="partial-add-trained"]'
        )
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", add_btn
        )
        add_btn.click()
        self.wait.until(self.document_loaded())

        self._fill_trained_aidant_email(1, trained_aidant2.email)
        self._submit_trained_form_next()
        self.wait.until(self.document_loaded())

        self._submit_trained_form_next()

        self._confirm_wizard(
            expected_texts=self.ALREADY_TRAINED_EXPECTED,
            unexpected_texts=self.ALREADY_TRAINED_UNEXPECTED,
        )

        self.assertEqual(2, StructureChangeRequest.objects.count())
        emails = set(StructureChangeRequest.objects.values_list("email", flat=True))
        self.assertEqual(
            {self.trained_aidant.email.lower(), trained_aidant2.email.lower()}, emails
        )
