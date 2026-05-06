import re
from datetime import timedelta

from django.db import transaction
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils.timezone import now

from aidants_connect_common.models import Formation
from aidants_connect_common.tests.factories import FormationFactory
from aidants_connect_web.constants import (
    AddAidantProfileChoice,
    HabilitationRequestCourseType,
    ReferentRequestStatuses,
    StructureChangeRequestStatuses,
)
from aidants_connect_web.models import HabilitationRequest, StructureChangeRequest
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)
from aidants_connect_web.views.espace_responsable import (
    SESSION_KEY_ADD_AIDANT_WIZARD,
    AddAidantProfileChoiceView,
    FormationRegistrationView,
)


@tag("responsable-structure")
class HabilitationRequestsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Tom is référent of organisations A and B
        cls.responsable_tom = AidantFactory()
        cls.org_a = cls.responsable_tom.organisation
        cls.org_b = OrganisationFactory(name="B")
        cls.responsable_tom.responsable_de.add(cls.org_a)
        cls.responsable_tom.responsable_de.add(cls.org_b)
        cls.responsable_tom.can_create_mandats = False
        cls.add_aidant_url = reverse("espace_referent:aidant_new_profile")
        cls.add_aidant_trained_url = reverse("espace_referent:aidant_new_trained")
        cls.add_aidant_untrained_url = reverse("espace_referent:aidant_new_untrained")
        cls.add_aidant_confirmation_url = reverse(
            "espace_referent:aidant_new_confirmation"
        )
        cls.organisation_url = reverse("espace_referent:organisation")
        cls.view_class = AddAidantProfileChoiceView
        cls.prefix = "multiform-habilitation_requests"

    def test_add_aidant_triggers_the_right_view(self):
        found = resolve(self.add_aidant_url)
        self.assertEqual(found.func.view_class, self.view_class)

    def test_add_aidant_step1_triggers_step1_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.add_aidant_url)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/add-aidant-wizard-step1.html",
        )

    def test_profile_page_resets_existing_wizard_session_data(self):
        self.client.force_login(self.responsable_tom)
        session = self.client.session
        session[SESSION_KEY_ADD_AIDANT_WIZARD] = {
            "profile_choice": AddAidantProfileChoice.ALREADY_TRAINED,
            "classic_data": {"some": "value"},
            "structure_change_data": [{"email": "old@example.com"}],
            "ready_for_confirmation": True,
        }
        session.save()

        response = self.client.get(self.add_aidant_url)
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertEqual(session.get(SESSION_KEY_ADD_AIDANT_WIZARD), {})

    def test_post_trained_without_profile_redirects_to_profile_and_clears_session(self):
        self.client.force_login(self.responsable_tom)
        session = self.client.session
        session[SESSION_KEY_ADD_AIDANT_WIZARD] = {"ready_for_confirmation": True}
        session.save()

        response = self.client.post(
            self.add_aidant_trained_url,
            data={"partial-add-trained": "1"},
        )
        self.assertRedirects(
            response, self.add_aidant_url, fetch_redirect_response=False
        )
        self.assertNotIn(SESSION_KEY_ADD_AIDANT_WIZARD, self.client.session)

    def test_confirmation_get_without_valid_profile_redirects_to_profile(self):
        self.client.force_login(self.responsable_tom)
        session = self.client.session
        session[SESSION_KEY_ADD_AIDANT_WIZARD] = {"ready_for_confirmation": True}
        session.save()

        response = self.client.get(self.add_aidant_confirmation_url)
        self.assertRedirects(
            response, self.add_aidant_url, fetch_redirect_response=False
        )
        self.assertNotIn(SESSION_KEY_ADD_AIDANT_WIZARD, self.client.session)

    def test_confirmation_post_without_valid_profile_redirects_to_profile(self):
        self.client.force_login(self.responsable_tom)
        session = self.client.session
        session[SESSION_KEY_ADD_AIDANT_WIZARD] = {"ready_for_confirmation": True}
        session.save()

        response = self.client.post(
            self.add_aidant_confirmation_url,
            data={"wizard_confirm": "1"},
        )
        self.assertRedirects(
            response, self.add_aidant_url, fetch_redirect_response=False
        )
        self.assertNotIn(SESSION_KEY_ADD_AIDANT_WIZARD, self.client.session)

    def test_confirmation_get_requires_expected_data_for_profile(self):
        self.client.force_login(self.responsable_tom)
        session = self.client.session
        session[SESSION_KEY_ADD_AIDANT_WIZARD] = {
            "profile_choice": AddAidantProfileChoice.NOT_YET_TRAINED,
            "ready_for_confirmation": True,
            # Missing classic_data should invalidate confirmation access
        }
        session.save()

        response = self.client.get(self.add_aidant_confirmation_url)
        self.assertRedirects(
            response, self.add_aidant_url, fetch_redirect_response=False
        )
        self.assertNotIn(SESSION_KEY_ADD_AIDANT_WIZARD, self.client.session)

    def test_add_another_trained_aidant_button_adds_formset_form(self):
        """Clicking 'Ajouter un autre aidant déjà habilité'
        adds a second form to the formset."""
        self.client.force_login(self.responsable_tom)
        # Go to trained view with profile ALREADY_TRAINED
        self.client.post(
            self.add_aidant_url,
            data={"profile": AddAidantProfileChoice.ALREADY_TRAINED},
        )
        get_response = self.client.get(self.add_aidant_trained_url)
        self.assertEqual(get_response.status_code, 200)
        formset = get_response.context["formset"]
        self.assertEqual(len(formset.forms), 1, "Step 2 should start with one form")

        # POST with "add another" button: formset should get one more form
        post_data = {
            "partial-add-trained": "1",
            # "csrfmiddlewaretoken": csrf_match.group(1),
            f"{formset.prefix}-TOTAL_FORMS": "1",
            f"{formset.prefix}-INITIAL_FORMS": "0",
            f"{formset.prefix}-MIN_NUM_FORMS": "0",
            f"{formset.prefix}-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/add-aidant-wizard-step2-trained.html",  # noqa: E501
        )
        formset_after = response.context["formset"]
        self.assertEqual(
            len(formset_after.forms),
            2,
            "Clicking 'Ajouter un autre aidant déjà habilité' should add a second form",
        )

    def test_habilitation_request_not_displayed_if_no_need(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "Demandes d'habilitation en cours",
            response_content,
            "Confirmation message should be displayed.",
        )

    def test_habilitation_request_is_displayed_if_needed(self):
        HabilitationRequestFactory(organisation=self.org_a)
        self.client.force_login(self.responsable_tom)
        response = self.client.get(reverse("espace_referent:aidants"))
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Demandes en cours",
            response_content,
            "Confirmation message should be displayed.",
        )

    def test_habilitation_request_p2p_processing_dont_display_formation_inscription(
        self,
    ):
        HabilitationRequestFactory(
            organisation=self.org_a,
            email="p2ptest@example.com",
            status=ReferentRequestStatuses.STATUS_PROCESSING_P2P,
            course_type=HabilitationRequestCourseType.P2P,
        )
        self.client.force_login(self.responsable_tom)
        response = self.client.get(reverse("espace_referent:aidants"))
        response_content = response.content.decode("utf-8")
        self.assertIn("Validée", response_content)
        self.assertIn("Formation pair à pair", response_content)
        self.assertNotIn("Session du", response_content)
        self.assertNotIn("Inscrire à une session", response_content)

    def test_add_aidant_allows_create_aidants_for_all_possible_organisations(self):
        self.client.force_login(self.responsable_tom)
        for idx, organisation in enumerate(self.responsable_tom.responsable_de.all()):
            with transaction.atomic():
                self.responsable_tom.organisation = organisation
                self.responsable_tom.save()

            email = f"angela.dubois{organisation.id}@a.org"

            # Step 1: choose profile NOT_YET_TRAINED
            r1 = self.client.post(
                self.add_aidant_url,
                data={"profile": AddAidantProfileChoice.NOT_YET_TRAINED},
            )
            self.assertRedirects(
                r1, self.add_aidant_untrained_url, fetch_redirect_response=False
            )
            # Step 2: submit classic form
            r2 = self.client.post(
                self.add_aidant_untrained_url,
                data={
                    f"{self.prefix}-TOTAL_FORMS": "1",
                    f"{self.prefix}-INITIAL_FORMS": "0",
                    f"{self.prefix}-MIN_NUM_FORMS": "0",
                    f"{self.prefix}-MAX_NUM_FORMS": "1000",
                    f"{self.prefix}-0-id": "",
                    f"{self.prefix}-0-email": email,
                    f"{self.prefix}-0-first_name": "Angela",
                    f"{self.prefix}-0-last_name": "Dubois",
                    f"{self.prefix}-0-profession": "Assistante sociale",
                    f"{self.prefix}-0-organisation": f"{organisation.pk}",
                    f"{self.prefix}-0-conseiller_numerique": "False",
                    "multiform-course_type-type": "1",
                },
            )
            self.assertRedirects(
                r2, self.add_aidant_confirmation_url, fetch_redirect_response=False
            )
            # Step 3: confirm and send
            response = self.client.post(
                self.add_aidant_confirmation_url,
                data={"wizard_confirm": "1"},
            )
            self.assertRedirects(
                response,
                reverse("espace_referent:aidants"),
                fetch_redirect_response=False,
            )
            self.assertEqual(idx + 1, len(HabilitationRequest.objects.all()))
            response = self.client.get(reverse("espace_referent:aidants"))
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "Votre ou vos demande(s) ont été enregistrées avec succès",
                response_content,
                "Confirmation message should be displayed.",
            )
            created_habilitation_request = HabilitationRequest.objects.get(email=email)
            self.assertEqual(
                created_habilitation_request.origin,
                HabilitationRequest.ORIGIN_RESPONSABLE,
            )
            self.assertEqual(
                created_habilitation_request.status,
                ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
            )

    def _extract_input_value(self, html, field_name):
        """Extract the value attribute from an <input> with the given name."""
        pattern = rf'name="{re.escape(field_name)}"[^>]*\bvalue="([^"]*)"'
        m = re.search(pattern, html)
        if m:
            return m.group(1)
        pattern2 = rf'value="([^"]*)"[^>]*name="{re.escape(field_name)}"'
        m2 = re.search(pattern2, html)
        return m2.group(1) if m2 else None

    def _extract_select_value(self, html, field_name):
        """Extract the selected option value from a <select> with the given name."""
        select_pattern = (
            rf'<select[^>]*name="{re.escape(field_name)}"[^>]*>(.*?)</select>'
        )
        m = re.search(select_pattern, html, re.DOTALL)
        if not m:
            return None
        selected = re.search(r'<option[^>]*value="([^"]*)"[^>]*selected', m.group(1))
        return selected.group(1) if selected else None

    def test_back_navigation_preserves_data_on_second_round_trip(self):
        """Going forward→back→forward→back must show all aidants every time."""
        self.client.force_login(self.responsable_tom)

        # Step 1: choose NOT_YET_TRAINED
        self.client.post(
            self.add_aidant_url,
            data={"profile": AddAidantProfileChoice.NOT_YET_TRAINED},
        )

        # Step 2: POST 2 aidants
        post_data = {
            f"{self.prefix}-TOTAL_FORMS": "2",
            f"{self.prefix}-INITIAL_FORMS": "0",
            f"{self.prefix}-MIN_NUM_FORMS": "0",
            f"{self.prefix}-MAX_NUM_FORMS": "1000",
            f"{self.prefix}-0-id": "",
            f"{self.prefix}-0-email": "aidant1@example.com",
            f"{self.prefix}-0-first_name": "Alice",
            f"{self.prefix}-0-last_name": "Martin",
            f"{self.prefix}-0-profession": "Assistante sociale",
            f"{self.prefix}-0-organisation": str(self.org_a.pk),
            f"{self.prefix}-0-conseiller_numerique": "False",
            f"{self.prefix}-1-id": "",
            f"{self.prefix}-1-email": "aidant2@example.com",
            f"{self.prefix}-1-first_name": "Bob",
            f"{self.prefix}-1-last_name": "Dupont",
            f"{self.prefix}-1-profession": "Médiateur numérique",
            f"{self.prefix}-1-organisation": str(self.org_a.pk),
            f"{self.prefix}-1-conseiller_numerique": "False",
            "multiform-course_type-type": "1",
        }
        r = self.client.post(self.add_aidant_untrained_url, data=post_data)
        self.assertRedirects(
            r,
            self.add_aidant_confirmation_url,
            fetch_redirect_response=False,
            msg_prefix="First POST should redirect to confirmation",
        )

        # First back: GET untrained → should show 2 aidants
        r = self.client.get(self.add_aidant_untrained_url)
        self.assertEqual(r.status_code, 200)
        formset = r.context["form"]["habilitation_requests"]
        self.assertEqual(
            len(formset.forms),
            2,
            "First back: should display 2 aidant forms",
        )

        # Verify the ACTUAL HTML has the correct field values for BOTH forms
        html = r.content.decode()
        self.assertEqual(
            self._extract_input_value(html, f"{self.prefix}-0-email"),
            "aidant1@example.com",
            "Form 0: email should be in HTML",
        )
        self.assertEqual(
            self._extract_input_value(html, f"{self.prefix}-1-email"),
            "aidant2@example.com",
            "Form 1: email should be in HTML",
        )
        self.assertEqual(
            self._extract_input_value(html, f"{self.prefix}-1-first_name"),
            "Bob",
            "Form 1: first_name should be in HTML",
        )
        self.assertEqual(
            self._extract_input_value(html, f"{self.prefix}-1-last_name"),
            "Dupont",
            "Form 1: last_name should be in HTML",
        )
        self.assertEqual(
            self._extract_select_value(html, f"{self.prefix}-1-organisation"),
            str(self.org_a.pk),
            "Form 1: organisation should be selected in HTML",
        )

        # Now re-submit using data EXTRACTED from the HTML (like a browser would)
        mgmt_prefix = formset.management_form.prefix
        repost_data = {
            f"{mgmt_prefix}-TOTAL_FORMS": "2",
            f"{mgmt_prefix}-INITIAL_FORMS": "0",
            f"{mgmt_prefix}-MIN_NUM_FORMS": "0",
            f"{mgmt_prefix}-MAX_NUM_FORMS": "1000",
            "multiform-course_type-type": "1",
        }
        for i in range(2):
            repost_data[f"{self.prefix}-{i}-id"] = (
                self._extract_input_value(html, f"{self.prefix}-{i}-id") or ""
            )
            repost_data[f"{self.prefix}-{i}-email"] = (
                self._extract_input_value(html, f"{self.prefix}-{i}-email") or ""
            )
            repost_data[f"{self.prefix}-{i}-first_name"] = (
                self._extract_input_value(html, f"{self.prefix}-{i}-first_name") or ""
            )
            repost_data[f"{self.prefix}-{i}-last_name"] = (
                self._extract_input_value(html, f"{self.prefix}-{i}-last_name") or ""
            )
            repost_data[f"{self.prefix}-{i}-profession"] = (
                self._extract_input_value(html, f"{self.prefix}-{i}-profession") or ""
            )
            repost_data[f"{self.prefix}-{i}-organisation"] = (
                self._extract_select_value(html, f"{self.prefix}-{i}-organisation")
                or ""
            )
            # For radio buttons, find which one is checked
            cn_pattern = rf'name="{re.escape(self.prefix)}-{i}-conseiller_numerique"\s+value="([^"]*)"[^>]*checked'  # noqa: E501
            cn_match = re.search(cn_pattern, html)
            repost_data[f"{self.prefix}-{i}-conseiller_numerique"] = (
                cn_match.group(1) if cn_match else ""
            )

        # Verify we extracted real data before posting
        self.assertEqual(
            repost_data[f"{self.prefix}-1-email"],
            "aidant2@example.com",
            "Extracted email for form 1 should not be empty",
        )

        r2 = self.client.post(self.add_aidant_untrained_url, data=repost_data)
        self.assertRedirects(
            r2,
            self.add_aidant_confirmation_url,
            fetch_redirect_response=False,
            msg_prefix="Second POST should also redirect to confirmation",
        )

        # Second back: GET untrained → should STILL show 2 aidants
        r3 = self.client.get(self.add_aidant_untrained_url)
        self.assertEqual(r3.status_code, 200)
        formset2 = r3.context["form"]["habilitation_requests"]
        self.assertEqual(
            len(formset2.forms),
            2,
            "Second back: should still display 2 aidant forms",
        )
        html3 = r3.content.decode()
        self.assertEqual(
            self._extract_input_value(html3, f"{self.prefix}-1-email"),
            "aidant2@example.com",
            "Second back: form 1 email should still be in HTML",
        )

    def _wizard_post_none_trained_flow(self, untrained_data):
        """POST profile (NOT_YET_TRAINED), then untrained view, then confirmation."""
        self.client.post(
            self.add_aidant_url,
            data={"profile": AddAidantProfileChoice.NOT_YET_TRAINED},
        )
        self.client.post(self.add_aidant_untrained_url, data=untrained_data)
        return self.client.post(
            self.add_aidant_confirmation_url,
            data={"wizard_confirm": "1"},
        )

    def test_email_is_lowercased(self):
        self.client.force_login(self.responsable_tom)
        uppercased_email = "Angela.DUBOIS@doe.du"
        lowercased_email = "angela.dubois@doe.du"

        data = {
            f"{self.prefix}-TOTAL_FORMS": "1",
            f"{self.prefix}-INITIAL_FORMS": "0",
            f"{self.prefix}-MIN_NUM_FORMS": "0",
            f"{self.prefix}-MAX_NUM_FORMS": "1000",
            f"{self.prefix}-0-id": "",
            f"{self.prefix}-0-email": uppercased_email,
            f"{self.prefix}-0-first_name": "Angela",
            f"{self.prefix}-0-last_name": "Dubois",
            f"{self.prefix}-0-profession": "Assistante sociale",
            f"{self.prefix}-0-organisation": f"{self.org_a.id}",
            f"{self.prefix}-0-conseiller_numerique": "False",
            "multiform-course_type-type": "1",
        }

        self._wizard_post_none_trained_flow(data)

        last_request = HabilitationRequest.objects.last()
        self.assertEqual(last_request.email, lowercased_email)

    def test_check_p2p_trainer_is_a_real_aidant(self):
        self.client.force_login(self.responsable_tom)
        real_trainer = AidantFactory(email="realtrainer@example.com")

        data = {
            f"{self.prefix}-TOTAL_FORMS": "1",
            f"{self.prefix}-INITIAL_FORMS": "0",
            f"{self.prefix}-MIN_NUM_FORMS": "0",
            f"{self.prefix}-MAX_NUM_FORMS": "1000",
            f"{self.prefix}-0-id": "",
            f"{self.prefix}-0-email": "angela.dubois@doe.du",
            f"{self.prefix}-0-first_name": "Angela",
            f"{self.prefix}-0-last_name": "Dubois",
            f"{self.prefix}-0-profession": "Assistante sociale",
            f"{self.prefix}-0-organisation": f"{self.org_a.id}",
            f"{self.prefix}-0-conseiller_numerique": "False",
            "multiform-course_type-type": "2",
            "multiform-course_type-email_formateur": real_trainer.email,
        }

        self._wizard_post_none_trained_flow(data)

        self.assertEqual(HabilitationRequest.objects.count(), 1)
        self.assertEqual(
            HabilitationRequest.objects.first().email, "angela.dubois@doe.du"
        )

    def test_fail_if_p2p_trainer_is_not_a_real_aidant(self):
        self.client.force_login(self.responsable_tom)
        fake_trainer_email = "faketrainer@example.com"

        data = {
            f"{self.prefix}-TOTAL_FORMS": "1",
            f"{self.prefix}-INITIAL_FORMS": "0",
            f"{self.prefix}-MIN_NUM_FORMS": "0",
            f"{self.prefix}-MAX_NUM_FORMS": "1000",
            f"{self.prefix}-0-id": "",
            f"{self.prefix}-0-email": "angela.dubois_fake_trainer@doe.du",
            f"{self.prefix}-0-first_name": "Angela",
            f"{self.prefix}-0-last_name": "Dubois",
            f"{self.prefix}-0-profession": "Assistante sociale",
            f"{self.prefix}-0-organisation": f"{self.org_a.id}",
            f"{self.prefix}-0-conseiller_numerique": "False",
            "multiform-course_type-type": "2",
            "multiform-course_type-email_formateur": fake_trainer_email,
        }

        self._wizard_post_none_trained_flow(data)

        self.assertEqual(HabilitationRequest.objects.count(), 0)

    def test_submit_habilitation_request_for_same_email_and_sister_organisation(self):
        self.client.force_login(self.responsable_tom)

        hr: HabilitationRequest = HabilitationRequestFactory(
            organisation=self.org_a, email="b@b.fr"
        )

        # Reach untrained view via wizard
        self.client.post(
            self.add_aidant_url,
            data={"profile": AddAidantProfileChoice.NOT_YET_TRAINED},
        )
        response = self.client.post(
            self.add_aidant_untrained_url,
            data={
                f"{self.prefix}-TOTAL_FORMS": "1",
                f"{self.prefix}-INITIAL_FORMS": "0",
                f"{self.prefix}-MIN_NUM_FORMS": "0",
                f"{self.prefix}-MAX_NUM_FORMS": "1000",
                f"{self.prefix}-0-id": "",
                f"{self.prefix}-0-email": hr.email,
                f"{self.prefix}-0-first_name": "Angela",
                f"{self.prefix}-0-last_name": "Dubois",
                f"{self.prefix}-0-profession": "Assistante sociale",
                f"{self.prefix}-0-organisation": f"{self.org_b.id}",
                f"{self.prefix}-0-conseiller_numerique": "False",
                "multiform-course_type-type": "1",
            },
        )
        self.assertEqual(response.status_code, 200, "Response should not be redirected")
        self.assertFormError(
            response.context_data["form"]["habilitation_requests"].extra_forms[0],
            "email",
            errors=[
                (
                    "Erreur : une demande d’habilitation est déjà en cours "
                    "pour l’adresse e-mail. Vous n’avez pas besoin de déposer "
                    "une nouvelle demande pour cette adresse-ci."
                )
            ],
        )

    def test_submitting_habilitation_request_if_aidant_already_exists(self):
        self.client.force_login(self.responsable_tom)

        existing_aidant = AidantFactory(organisation=self.org_a)

        # Reach untrained view via wizard
        self.client.post(
            self.add_aidant_url,
            data={"profile": AddAidantProfileChoice.NOT_YET_TRAINED},
        )
        response = self.client.post(
            self.add_aidant_untrained_url,
            data={
                f"{self.prefix}-TOTAL_FORMS": "1",
                f"{self.prefix}-INITIAL_FORMS": "0",
                f"{self.prefix}-MIN_NUM_FORMS": "0",
                f"{self.prefix}-MAX_NUM_FORMS": "1000",
                f"{self.prefix}-0-id": "",
                f"{self.prefix}-0-email": existing_aidant.email,
                f"{self.prefix}-0-first_name": "Bob",
                f"{self.prefix}-0-last_name": "Dubois",
                f"{self.prefix}-0-profession": "Assistant",
                f"{self.prefix}-0-organisation": f"{self.org_b.id}",
                f"{self.prefix}-0-conseiller_numerique": "False",
                "multiform-course_type-type": "1",
            },
        )
        self.assertEqual(response.status_code, 200, "Response should not be redirected")
        self.assertFormError(
            response.context_data["form"]["habilitation_requests"].extra_forms[0],
            "email",
            errors=[
                (
                    "Erreur : il existe déjà un compte aidant pour cette "
                    "adresse e-mail. Vous n’avez pas besoin de déposer une "
                    "nouvelle demande pour cette adresse-ci."
                )
            ],
        )

    def test_avoid_oracle_for_other_organisations_requests(self):
        self.client.force_login(self.responsable_tom)

        HabilitationRequestFactory(organisation=OrganisationFactory(), email="b@b.fr")

        response = self._wizard_post_none_trained_flow(
            {
                f"{self.prefix}-TOTAL_FORMS": "1",
                f"{self.prefix}-INITIAL_FORMS": "0",
                f"{self.prefix}-MIN_NUM_FORMS": "0",
                f"{self.prefix}-MAX_NUM_FORMS": "1000",
                f"{self.prefix}-0-id": "",
                f"{self.prefix}-0-email": "b@b.fr",
                f"{self.prefix}-0-first_name": "Bob",
                f"{self.prefix}-0-last_name": "Dubois",
                f"{self.prefix}-0-profession": "Assistant",
                f"{self.prefix}-0-organisation": f"{self.org_a.id}",
                f"{self.prefix}-0-conseiller_numerique": "False",
                "multiform-course_type-type": "1",
            }
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:aidants"),
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("espace_referent:aidants"))
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Votre ou vos demande(s) ont été enregistrées avec succès",
            response_content,
            "Confirmation message should be displayed.",
        )

    def test_avoid_oracle_for_other_organisations_aidants(self):
        self.client.force_login(self.responsable_tom)

        other_aidant = AidantFactory()

        response = self._wizard_post_none_trained_flow(
            {
                f"{self.prefix}-TOTAL_FORMS": "1",
                f"{self.prefix}-INITIAL_FORMS": "0",
                f"{self.prefix}-MIN_NUM_FORMS": "0",
                f"{self.prefix}-MAX_NUM_FORMS": "1000",
                f"{self.prefix}-0-id": "",
                f"{self.prefix}-0-email": other_aidant.email,
                f"{self.prefix}-0-first_name": "Bob",
                f"{self.prefix}-0-last_name": "Dubois",
                f"{self.prefix}-0-profession": "Assistant sociale",
                f"{self.prefix}-0-organisation": f"{self.org_a.id}",
                f"{self.prefix}-0-conseiller_numerique": "False",
                "multiform-course_type-type": "1",
            }
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:aidants"),
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("espace_referent:aidants"))
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Votre ou vos demande(s) ont été enregistrées avec succès",
            response_content,
            "Confirmation message should be displayed.",
        )


@tag("responsable-structure")
class AlreadyTrainedStructureChangeRequestTests(TestCase):
    """Tests for the ALREADY_TRAINED wizard workflow (StructureChangeRequest only)."""

    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.responsable = AidantFactory()
        cls.org = cls.responsable.organisation
        cls.org_b = OrganisationFactory(name="Org B")
        cls.responsable.responsable_de.add(cls.org)
        cls.responsable.responsable_de.add(cls.org_b)
        cls.responsable.can_create_mandats = False

        cls.trained_aidant = AidantFactory(
            organisation=OrganisationFactory(name="External Org")
        )
        cls.trained_aidant2 = AidantFactory(
            organisation=OrganisationFactory(name="External Org 2")
        )

        cls.add_aidant_url = reverse("espace_referent:aidant_new_profile")
        cls.add_aidant_trained_url = reverse("espace_referent:aidant_new_trained")
        cls.add_aidant_confirmation_url = reverse(
            "espace_referent:aidant_new_confirmation"
        )
        cls.formset_prefix = "form"

    def _start_already_trained_wizard(self):
        self.client.post(
            self.add_aidant_url,
            data={"profile": AddAidantProfileChoice.ALREADY_TRAINED},
        )

    def _build_trained_post_data(
        self, entries, total_forms=None, with_lookup_done=False
    ):
        """Build POST data for the trained formset.
        entries: list of dicts with keys email, email_will_change, new_email.
        """
        prefix = self.formset_prefix
        if total_forms is None:
            total_forms = len(entries)
        data = {
            f"{prefix}-TOTAL_FORMS": str(total_forms),
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }
        for i, entry in enumerate(entries):
            data[f"{prefix}-{i}-email"] = entry.get("email", "")
            if entry.get("email_will_change") is not None:
                data[f"{prefix}-{i}-email_will_change"] = str(
                    entry.get("email_will_change")
                )
            data[f"{prefix}-{i}-new_email"] = entry.get("new_email", "")
            if with_lookup_done:
                data[f"{prefix}-{i}-email_lookup_done"] = "on"
        return data

    def _wizard_already_trained_to_confirmation(self, entries):
        """Run the ALREADY_TRAINED wizard up to the confirmation page (GET)."""
        self._start_already_trained_wizard()
        post_data = self._build_trained_post_data(entries)
        self.client.post(self.add_aidant_trained_url, data=post_data)
        post_data = self._build_trained_post_data(entries, with_lookup_done=True)
        self.client.post(self.add_aidant_trained_url, data=post_data)
        return self.client.get(self.add_aidant_confirmation_url)

    def _wizard_already_trained_flow(self, entries):
        """Run the full ALREADY_TRAINED wizard:
        profile → trained (lookup) → trained (confirm) → confirmation."""
        self._wizard_already_trained_to_confirmation(entries)
        return self.client.post(
            self.add_aidant_confirmation_url,
            data={"wizard_confirm": "1"},
        )

    def test_all_trained_creates_structure_change_request(self):
        self.client.force_login(self.responsable)
        response = self._wizard_already_trained_flow(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                }
            ]
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:aidants"),
            fetch_redirect_response=False,
        )
        self.assertEqual(1, StructureChangeRequest.objects.count())
        scr = StructureChangeRequest.objects.first()
        self.assertEqual(self.trained_aidant.email.lower(), scr.email)
        self.assertEqual(self.org, scr.organisation)
        self.assertEqual(self.trained_aidant, scr.aidant)
        self.assertFalse(scr.new_email)
        self.assertEqual(scr.status, StructureChangeRequestStatuses.STATUS_NEW.value)
        self.assertEqual(0, HabilitationRequest.objects.count())

    def test_all_trained_with_email_change(self):
        self.client.force_login(self.responsable)
        response = self._wizard_already_trained_flow(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": True,
                    "new_email": "new-address@example.com",
                }
            ]
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:aidants"),
            fetch_redirect_response=False,
        )
        scr = StructureChangeRequest.objects.first()
        self.assertEqual(self.trained_aidant.email.lower(), scr.email)
        self.assertEqual("new-address@example.com", scr.new_email)

    def test_all_trained_new_email_already_used_rejected(self):
        taken_address = "taken-for-new-email@example.com"
        other = AidantFactory(
            organisation=OrganisationFactory(),
            username=taken_address,
            email=taken_address,
        )
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        entries = [
            {
                "email": self.trained_aidant.email,
                "email_will_change": True,
                "new_email": other.email,
            }
        ]
        post_data = self._build_trained_post_data(entries)
        self.client.post(self.add_aidant_trained_url, data=post_data)
        post_data = self._build_trained_post_data(entries, with_lookup_done=True)
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_email_change_without_new_email_displays_error(self):
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        entries = [
            {
                "email": self.trained_aidant.email,
                "email_will_change": True,
                "new_email": "",
            }
        ]

        # First POST performs lookup and shows contextual message.
        post_data = self._build_trained_post_data(entries)
        self.client.post(self.add_aidant_trained_url, data=post_data)

        # Second POST enforces required new_email once lookup is done.
        post_data = self._build_trained_post_data(entries, with_lookup_done=True)
        response = self.client.post(self.add_aidant_trained_url, data=post_data)

        self.assertEqual(200, response.status_code)
        form = response.context["formset"].forms[0]
        self.assertFormError(
            form,
            "new_email",
            "Ce champ est obligatoire lorsque l'e-mail est différent.",
        )
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_multiple_aidants(self):
        self.client.force_login(self.responsable)
        response = self._wizard_already_trained_flow(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                },
                {
                    "email": self.trained_aidant2.email,
                    "email_will_change": False,
                },
            ]
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:aidants"),
            fetch_redirect_response=False,
        )
        self.assertEqual(2, StructureChangeRequest.objects.count())
        emails = set(StructureChangeRequest.objects.values_list("email", flat=True))
        self.assertEqual(
            {self.trained_aidant.email.lower(), self.trained_aidant2.email.lower()},
            emails,
        )

    def test_all_trained_invalid_email_stays_on_form(self):
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        post_data = self._build_trained_post_data(
            [
                {
                    "email": "nonexistent@example.com",
                    "email_will_change": False,
                }
            ]
        )
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/add-aidant-wizard-step2-trained.html",  # noqa: E501
        )
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_referent_only_account_rejected(self):
        referent_only = AidantFactory(
            organisation=OrganisationFactory(),
            referent_non_aidant=True,
            can_create_mandats=False,
        )
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        post_data = self._build_trained_post_data(
            [
                {
                    "email": referent_only.email,
                    "email_will_change": False,
                }
            ]
        )
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_duplicate_email_in_formset(self):
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        post_data = self._build_trained_post_data(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                },
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                },
            ]
        )
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_existing_structure_change_request_rejected(self):
        scr = StructureChangeRequest.objects.create(
            aidant=self.trained_aidant,
            email=self.trained_aidant.email,
            organisation=self.org,
        )
        scr.previous_organisations.add(self.trained_aidant.organisation)
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        post_data = self._build_trained_post_data(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                }
            ]
        )
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        # No new request: the form should have rejected it
        self.assertEqual(1, StructureChangeRequest.objects.count())

    def test_all_trained_aidant_already_in_org_rejected(self):
        aidant_in_org = AidantFactory(organisation=self.org)
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        post_data = self._build_trained_post_data(
            [
                {
                    "email": aidant_in_org.email,
                    "email_will_change": False,
                }
            ]
        )
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, StructureChangeRequest.objects.count())

    def test_all_trained_aidant_in_multiple_organisations_allowed(self):
        aidant_multi_org = AidantFactory(organisation=OrganisationFactory())
        aidant_multi_org.organisations.add(OrganisationFactory(name="Another Org"))

        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        entries = [
            {
                "email": aidant_multi_org.email,
                "email_will_change": False,
            }
        ]
        post_data = self._build_trained_post_data(entries)
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code, "First POST triggers lookup")

        post_data = self._build_trained_post_data(entries, with_lookup_done=True)
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertRedirects(
            response,
            self.add_aidant_confirmation_url,
            fetch_redirect_response=False,
        )
        confirm_response = self.client.post(
            self.add_aidant_confirmation_url,
            data={"wizard_confirm": "1"},
        )
        self.assertRedirects(
            confirm_response,
            reverse("espace_referent:aidants"),
            fetch_redirect_response=False,
        )
        self.assertEqual(1, StructureChangeRequest.objects.count())
        scr = StructureChangeRequest.objects.first()
        expected_previous = set(
            aidant_multi_org.organisations.exclude(pk=self.org.pk).values_list(
                "pk", flat=True
            )
        )
        self.assertSetEqual(
            set(scr.previous_organisations.values_list("pk", flat=True)),
            expected_previous,
        )

    def test_all_trained_confirmation_shows_success_message(self):
        self.client.force_login(self.responsable)
        self._wizard_already_trained_flow(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                }
            ]
        )
        response = self.client.get(reverse("espace_referent:aidants"))
        self.assertContains(
            response,
            "Votre ou vos demande(s) ont été enregistrées avec succès",
        )

    def test_referent_of_other_org_directly_adds_aidant(self):
        """Case 1: aidant belongs to an org where the referent is also a
        manager → directly attached, no StructureChangeRequest created."""
        aidant_in_managed_org = AidantFactory(organisation=self.org_b)
        self.client.force_login(self.responsable)
        self._wizard_already_trained_flow([{"email": aidant_in_managed_org.email}])
        self.assertEqual(0, StructureChangeRequest.objects.count())
        self.assertIn(
            self.org,
            aidant_in_managed_org.organisations.all(),
            "Aidant should have been added to the current organisation",
        )

    def test_referent_of_other_org_shows_success_message(self):
        aidant_in_managed_org = AidantFactory(organisation=self.org_b)
        self.client.force_login(self.responsable)
        self._wizard_already_trained_flow([{"email": aidant_in_managed_org.email}])
        response = self.client.get(reverse("espace_referent:aidants"))
        self.assertContains(
            response,
            "Votre ou vos demande(s) ont été enregistrées avec succès",
        )

    def test_mixed_direct_add_and_structure_request(self):
        """Mix of case 1 (direct) and case 2 (request) in the same formset."""
        aidant_managed = AidantFactory(organisation=self.org_b)
        self.client.force_login(self.responsable)
        self._wizard_already_trained_flow(
            [
                {"email": aidant_managed.email},
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                },
            ]
        )
        self.assertEqual(1, StructureChangeRequest.objects.count())
        scr = StructureChangeRequest.objects.first()
        self.assertEqual(self.trained_aidant.email.lower(), scr.email)
        self.assertIn(self.org, aidant_managed.organisations.all())
        response = self.client.get(reverse("espace_referent:aidants"))
        self.assertContains(
            response,
            "Votre ou vos demande(s) ont été enregistrées avec succès",
        )

    def test_all_trained_add_another_button(self):
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        get_response = self.client.get(self.add_aidant_trained_url)
        formset = get_response.context["formset"]
        self.assertEqual(1, len(formset.forms))

        post_data = {
            "partial-add-trained": "1",
            f"{self.formset_prefix}-TOTAL_FORMS": "1",
            f"{self.formset_prefix}-INITIAL_FORMS": "0",
            f"{self.formset_prefix}-MIN_NUM_FORMS": "0",
            f"{self.formset_prefix}-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertEqual(200, response.status_code)
        formset_after = response.context["formset"]
        self.assertEqual(2, len(formset_after.forms))

    def test_all_trained_back_navigation_preserves_data(self):
        self.client.force_login(self.responsable)
        self._start_already_trained_wizard()
        entries = [
            {
                "email": self.trained_aidant.email,
                "email_will_change": False,
            }
        ]

        # First POST: email lookup (re-render)
        post_data = self._build_trained_post_data(entries)
        self.client.post(self.add_aidant_trained_url, data=post_data)

        # Second POST: with lookup done → redirect to confirmation
        post_data = self._build_trained_post_data(entries, with_lookup_done=True)
        r = self.client.post(self.add_aidant_trained_url, data=post_data)
        self.assertRedirects(
            r, self.add_aidant_confirmation_url, fetch_redirect_response=False
        )

        # Going back should restore the form with the aidant data
        back_response = self.client.get(self.add_aidant_trained_url)
        self.assertEqual(200, back_response.status_code)
        formset = back_response.context["formset"]
        self.assertEqual(1, len(formset.forms))
        html = back_response.content.decode()
        self.assertIn(self.trained_aidant.email.lower(), html)

    def test_all_trained_without_profile_redirects(self):
        self.client.force_login(self.responsable)
        response = self.client.post(
            self.add_aidant_trained_url,
            data=self._build_trained_post_data(
                [
                    {
                        "email": self.trained_aidant.email,
                        "email_will_change": False,
                    }
                ]
            ),
        )
        self.assertRedirects(
            response, self.add_aidant_url, fetch_redirect_response=False
        )

    def test_all_trained_previous_organisations_are_recorded(self):
        self.client.force_login(self.responsable)
        self._wizard_already_trained_flow(
            [
                {
                    "email": self.trained_aidant.email,
                    "email_will_change": False,
                }
            ]
        )
        scr = StructureChangeRequest.objects.first()
        expected = set(
            self.trained_aidant.organisations.exclude(pk=self.org.pk).values_list(
                "pk", flat=True
            )
        )
        self.assertSetEqual(
            set(scr.previous_organisations.values_list("pk", flat=True)),
            expected,
        )

    def test_all_trained_email_is_lowercased(self):
        self.client.force_login(self.responsable)
        self._wizard_already_trained_flow(
            [
                {
                    "email": self.trained_aidant.email.upper(),
                    "email_will_change": False,
                }
            ]
        )
        scr = StructureChangeRequest.objects.first()
        self.assertEqual(scr.email, self.trained_aidant.email.lower())

    def test_confirmation_page_direct_add_only(self):
        """When all aidants are case 1 (referent_of_other_org), the confirmation
        page shows only the direct-add message, not the request message."""
        aidant_in_managed_org = AidantFactory(organisation=self.org_b)
        self.client.force_login(self.responsable)
        response = self._wizard_already_trained_to_confirmation(
            [{"email": aidant_in_managed_org.email}]
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [aidant_in_managed_org.email.lower()],
            [item["email"] for item in response.context["direct_adds"]],
        )
        self.assertEqual([], list(response.context["structure_requests"]))
        self.assertContains(
            response,
            "Les aidants suivants vont être ajoutés à l'organisation",
        )
        self.assertContains(response, aidant_in_managed_org.email.lower())
        self.assertNotContains(
            response,
            "La demande d'ajout, pour les aidants suivants, "
            "sera vérifiée par notre équipe",
        )
        self.assertContains(response, "Confirmer l'ajout")
        self.assertNotContains(response, "Envoyer la demande")

    def test_confirmation_page_structure_request_only(self):
        """When all aidants are case 2 (other_org), the confirmation page shows
        only the request message, not the direct-add message."""
        self.client.force_login(self.responsable)
        response = self._wizard_already_trained_to_confirmation(
            [{"email": self.trained_aidant.email, "email_will_change": False}]
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual([], list(response.context["direct_adds"]))
        self.assertEqual(
            [self.trained_aidant.email.lower()],
            [item["email"] for item in response.context["structure_requests"]],
        )
        self.assertContains(
            response,
            "La demande d'ajout, pour les aidants suivants, "
            "sera vérifiée par notre équipe",
        )
        self.assertContains(response, self.trained_aidant.email.lower())
        self.assertNotContains(
            response,
            "Les aidants suivants vont être ajoutés à l'organisation",
        )
        self.assertContains(response, "Envoyer la demande")

    def test_confirmation_page_mixed_cases(self):
        """When both case 1 and case 2 aidants are present, both messages
        appear on the confirmation page."""
        aidant_managed = AidantFactory(organisation=self.org_b)
        self.client.force_login(self.responsable)
        response = self._wizard_already_trained_to_confirmation(
            [
                {"email": aidant_managed.email},
                {"email": self.trained_aidant.email, "email_will_change": False},
            ]
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [aidant_managed.email.lower()],
            [item["email"] for item in response.context["direct_adds"]],
        )
        self.assertEqual(
            [self.trained_aidant.email.lower()],
            [item["email"] for item in response.context["structure_requests"]],
        )
        self.assertContains(
            response,
            "Les aidants suivants vont être ajoutés à l'organisation",
        )
        self.assertContains(
            response,
            "La demande d'ajout, pour les aidants suivants, "
            "sera vérifiée par notre équipe",
        )
        self.assertContains(response, aidant_managed.email.lower())
        self.assertContains(response, self.trained_aidant.email.lower())
        self.assertContains(response, "Envoyer la demande")


class TestFormationRegistrationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent = AidantFactory(post__is_organisation_manager=True)
        cls.unrelated_referent = AidantFactory(post__is_organisation_manager=True)

        cls.habilitation_waiting = HabilitationRequestFactory(
            organisation=cls.referent.organisation,
            status=ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
        )

        cls.habilitation_processing = HabilitationRequestFactory(
            organisation=cls.referent.organisation,
            status=ReferentRequestStatuses.STATUS_PROCESSING,
        )

        cls.formation_ok: Formation = FormationFactory(
            type_label="Des formations et des Hommes",
            start_datetime=now() + timedelta(days=46),
        )

        cls.formation_too_close: Formation = FormationFactory(
            type_label="À la Bonne Formation", start_datetime=now() + timedelta(days=1)
        )

        cls.formation_full: Formation = FormationFactory(
            type_label="A fond la Formation",
            start_datetime=now() + timedelta(days=46),
            max_attendants=1,
        )
        cls.formation_full.register_attendant(HabilitationRequestFactory())

        cls.hr_registered_to_2_formations = HabilitationRequestFactory(
            organisation=cls.referent.organisation,
            status=ReferentRequestStatuses.STATUS_PROCESSING,
        )

        cls.formation_with_aidant1: Formation = FormationFactory(
            type_label="Hein? formations",
            start_datetime=now() + timedelta(days=46),
            attendants=[cls.hr_registered_to_2_formations],
            max_attendants=10,
        )

        cls.formation_with_aidant2: Formation = FormationFactory(
            type_label="Formes Ah Scions",
            start_datetime=now() + timedelta(days=46),
            attendants=[cls.hr_registered_to_2_formations],
            max_attendants=10,
        )

    def test_triggers_correct_view(self):
        found = resolve(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )
        self.assertEqual(found.func.view_class, FormationRegistrationView)

    def test_renders_correct_template(self):
        self.client.force_login(self.referent)
        response = self.client.get(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )
        self.assertTemplateUsed(response, "formation/formation-registration.html")

    def avoid_oracle(self):
        self.client.force_login(self.unrelated_referent)
        response = resolve(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_cant_register_aidant_in_incorrect_state(self):
        self.client.force_login(self.referent)
        response = self.client.get(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_waiting.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_display_only_available_formations(self):
        self.client.force_login(self.referent)
        # Formation too close or already full should not be listed on the page
        response = self.client.get(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )

        self.assertIn(self.formation_ok.type.label, response.content.decode())
        self.assertNotIn(self.formation_too_close.type.label, response.content.decode())
        self.assertNotIn(self.formation_full.type.label, response.content.decode())

    def test_registration(self):
        self.client.force_login(self.referent)
        self.assertEqual(0, self.formation_ok.attendants.count())
        response = self.client.post(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            ),
            data={"formations": [self.formation_full.pk]},
        )
        self.formation_ok.refresh_from_db()
        self.assertTemplateUsed(response, "formation/formation-registration.html")
        self.assertEqual(0, self.formation_ok.attendants.count())
        self.assertIn("formations", response.context_data["form"].errors)

        response = self.client.post(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            ),
            data={"formations": [self.formation_too_close.pk]},
        )
        self.formation_ok.refresh_from_db()
        self.assertTemplateUsed(response, "formation/formation-registration.html")
        self.assertEqual(0, self.formation_ok.attendants.count())
        self.assertIn("formations", response.context_data["form"].errors)

        self.client.post(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            ),
            data={"formations": [self.formation_ok.pk]},
        )
        self.formation_ok.refresh_from_db()
        self.assertEqual(
            {self.habilitation_processing},
            {item.attendant for item in self.formation_ok.attendants.all()},
        )

    def test_unregistration(self):
        self.client.force_login(self.referent)
        self.assertEqual(
            {self.formation_with_aidant1, self.formation_with_aidant2},
            {
                fa.formation
                for fa in self.hr_registered_to_2_formations.formations.all()
            },
        )
        self.client.post(
            reverse(
                "espace_referent:register_formation",
                kwargs={"request_id": self.hr_registered_to_2_formations.pk},
            ),
            data={"formations": [self.formation_ok.pk, self.formation_with_aidant1.pk]},
        )
        self.assertEqual(
            {self.formation_with_aidant1, self.formation_ok},
            {
                fa.formation
                for fa in self.hr_registered_to_2_formations.formations.all()
            },
        )
