from django.template.defaultfilters import yesno
from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.forms import NewHabilitationRequestForm
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
        root_path = reverse("espace_responsable_organisation")

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

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

    def test_grouped_autorisations(self):
        root_path = reverse("espace_responsable_organisation")

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # Check button text
        button = self.selenium.find_element(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.pk}-from-organisation",
        )
        self.assertEqual(
            "Retirer l’aidant de l’organisation",
            button.text,
        )

        button = self.selenium.find_element(
            By.ID, f"remove-aidant-{self.aidant_active_with_card.pk}-from-organisation"
        )
        self.assertEqual("Désactiver l’aidant", button.text)

        self.assertElementNotFound(
            By.ID, f"remove-aidant-{self.aidant_responsable.pk}-from-organisation"
        )

        # Let's try those btns shall we?
        button.click()
        path = reverse(
            "espace_responsable_remove_aidant_from_organisation",
            kwargs={
                "organisation_id": self.organisation.pk,
                "aidant_id": self.aidant_active_with_card.pk,
            },
        )
        self.wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Confirmer']"
        ).click()

        self.wait.until(url_matches(f"^.+{root_path}$"))

        self.assertElementNotFound(
            By.ID, f"remove-aidant-{self.aidant_active_with_card.pk}-from-organisation"
        )

        self.selenium.find_element(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.pk}-from-organisation",
        ).click()
        path = reverse(
            "espace_responsable_remove_aidant_from_organisation",
            kwargs={
                "organisation_id": self.organisation.pk,
                "aidant_id": self.aidant_with_multiple_orgs.pk,
            },
        )
        self.wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Confirmer']"
        ).click()

        self.wait.until(url_matches(f"^.+{root_path}$"))

        self.assertElementNotFound(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.pk}-from-organisation",
        )

    def test_remove_card_from_aidant(self):
        root_path = reverse("espace_responsable_organisation")

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # First aidant: disabled
        self.assertIsNotNone(self.aidant_inactive_with_card.carte_totp)

        self.selenium.find_element(
            By.ID, f"manage-totp-cards-for-aidant-{self.aidant_inactive_with_card.pk}"
        ).click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_inactive_with_card.id},
            )
        )

        button1 = self.selenium.find_element(
            By.ID,
            f"remove-totp-card-from-aidant-{self.aidant_inactive_with_card.pk}",
        )
        self.assertEqual("Délier la carte physique", button1.text)

        button1.click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_aidant_remove_card",
                kwargs={"aidant_id": self.aidant_inactive_with_card.pk},
            )
        )

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Dissocier']"
        ).click()

        self.wait.until(self.path_matches("espace_responsable_organisation"))

        # Return on manage cards page
        self.selenium.find_element(
            By.ID, f"manage-totp-cards-for-aidant-{self.aidant_inactive_with_card.pk}"
        ).click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_inactive_with_card.id},
            )
        )
        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_inactive_with_card.pk}"
        )

        self.aidant_inactive_with_card.refresh_from_db()
        with self.assertRaises(Aidant.carte_totp.RelatedObjectDoesNotExist):
            self.aidant_inactive_with_card.carte_totp

        self.open_live_url(reverse("espace_responsable_organisation"))
        self.selenium.find_element(
            By.ID, f"manage-totp-cards-for-aidant-{self.aidant_active_with_card.pk}"
        ).click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_active_with_card.id},
            )
        )
        self.assertIsNotNone(self.aidant_active_with_card.carte_totp)
        button2 = self.selenium.find_element(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_with_card.pk}"
        )
        self.assertEqual("Délier la carte physique", button2.text)

        # First aidant: active
        button2.click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_aidant_remove_card",
                kwargs={"aidant_id": self.aidant_active_with_card.pk},
            )
        )

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Dissocier']"
        ).click()

        self.wait.until(self.path_matches("espace_responsable_organisation"))

        self.selenium.find_element(
            By.ID, f"manage-totp-cards-for-aidant-{self.aidant_active_with_card.pk}"
        ).click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_choose_totp",
                kwargs={"aidant_id": self.aidant_active_with_card.id},
            )
        )
        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_active_with_card.pk}"
        )

        self.aidant_active_with_card.refresh_from_db()
        with self.assertRaises(Aidant.carte_totp.RelatedObjectDoesNotExist):
            self.aidant_active_with_card.carte_totp


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
class NewHabilitationRequestTestsNoJS(FunctionalTestCase):
    js = False

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
                    "force_left_form_check": False,
                    "form_kwargs": {"referent": self.aidant_responsable},
                }
            }
        )

    def test_submit_form_errors(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)

        # First form is empty

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.ID, "add-aidant-to-request").click()
        self.wait.until(self.document_loaded())

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        self.assertEqual(len(self._all_visible_fields), len(errors))

        for error in errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # First form is not empty but not filled either
        self.open_live_url(self.path)

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(
            By.ID,
            self._left_form["email"].id_for_label,
        ).send_keys("test@test.test")
        self.selenium.find_element(By.ID, "add-aidant-to-request").click()
        self.wait.until(self.document_loaded())

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        self.assertEqual(len(self._all_visible_fields) - 1, len(errors))

        for error in errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # ----------------------------------------------------------------------------
        # Testing submit for button
        # ----------------------------------------------------------------------------

        # First form is not empty but not filled either
        self.open_live_url(self.path)

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.ID, "form-submit").click()
        self.wait.until(self.document_loaded())

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        self.assertEqual(len(self._all_visible_fields), len(errors))

        for error in errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # First form is not empty but not filled either
        self.open_live_url(self.path)
        self.selenium.find_element(
            By.ID,
            self._left_form["email"].id_for_label,
        ).send_keys("test@test.test")

        # unrequire fields to be able to submit
        for el in self.selenium.find_elements(By.CSS_SELECTOR, "[required]"):
            self.selenium.execute_script("arguments[0].removeAttribute('required')", el)

        self.selenium.find_element(By.ID, "form-submit").click()
        self.wait.until(self.document_loaded())

        errors = self.selenium.find_elements(By.CLASS_NAME, "errorlist")
        self.assertEqual(len(self._all_visible_fields) - 1, len(errors))

        for error in errors:
            self.assertIn("Ce champ est obligatoire.", error.text)

        # ----------------------------------------------------------------------------
        # Asserting not new habilitation was created
        # ----------------------------------------------------------------------------
        self.assertFalse(HabilitationRequest.objects.count())

    def test_submitting_request(self):
        self.open_live_url(self.path)
        self.login_aidant(self.aidant_responsable)
        req: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req, self._all_visible_fields, self._custom_getter)
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
        req: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req, self._all_visible_fields, self._custom_getter)
        self.selenium.find_element(By.ID, "add-aidant-to-request").click()
        self.wait.until(self.document_loaded())

        self.assertNormalizedStringEqual(
            f"{req.get_full_name()} {req.email}",
            self.selenium.find_element(By.CSS_SELECTOR, "#added-form-0 summary").text,
        )

        # open the <details>
        details = self.selenium.find_element(By.CSS_SELECTOR, "#added-form-0")
        self.selenium.execute_script("arguments[0].open = true;", details)
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
            details.find_element(By.CLASS_NAME, "details-content").text,
        )
        # Asserting not new habilitation was created
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
        req1: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req1, self._all_visible_fields, self._custom_getter)
        self.selenium.find_element(By.ID, "add-aidant-to-request").click()
        self.wait.until(self.document_loaded())

        self.assertNormalizedStringEqual(
            f"{req1.get_full_name()} {req1.email}",
            self.selenium.find_element(By.CSS_SELECTOR, "#added-form-0 summary").text,
        )

        # open the <details>
        details = self.selenium.find_element(By.CSS_SELECTOR, "#added-form-0")
        self.selenium.execute_script("arguments[0].open = true;", details)
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
            details.find_element(By.CLASS_NAME, "details-content").text,
        )
        # Asserting not new habilitation was created
        self.assertFalse(HabilitationRequest.objects.count())

        req2: HabilitationRequest = HabilitationRequestFactory.build(
            organisation=self.organisation
        )
        self.fill_form(req2, self._all_visible_fields, self._custom_getter)

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

    @property
    def _left_form(self):
        return self.empty_form["habilitation_requests"].left_form

    @property
    def _course_type_form(self):
        return self.empty_form["course_type"]

    @property
    def _all_visible_fields(self):
        return [
            *self._left_form.visible_fields(),
            *self._course_type_form.visible_fields(),
        ]

    @staticmethod
    def _custom_getter(data, field, default_getter):
        return (
            default_getter(data, "course_type")
            if field == "type"
            else default_getter(data, field)
        )


@tag("functional")
class NewHabilitationRequestTestsWithJS(NewHabilitationRequestTestsNoJS):
    """Same tests than NewHabilitationRequestTestsNoJS but with JS enabled"""

    js = True
