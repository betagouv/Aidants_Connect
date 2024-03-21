from datetime import timedelta

from django.db import transaction
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils.timezone import now

from aidants_connect_common.models import Formation
from aidants_connect_common.tests.factories import FormationFactory
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import HabilitationRequest
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)
from aidants_connect_web.views import espace_responsable
from aidants_connect_web.views.espace_responsable import FormationRegistrationView


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
        # URL
        cls.add_aidant_url = "/espace-responsable/aidant/ajouter/"
        cls.organisation_url = "/espace-responsable/organisation/"

    def test_add_aidant_triggers_the_right_view(self):
        found = resolve(self.add_aidant_url)
        self.assertEqual(
            found.func.view_class, espace_responsable.NewHabilitationRequest
        )

    def test_add_aidant_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.add_aidant_url)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/new-habilitation-request.html",
        )

    def test_habilitation_request_not_displayed_if_no_need(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "Demandes d’habilitation en cours",
            response_content,
            "Confirmation message should be displayed.",
        )

    def test_habilitation_request_is_displayed_if_needed(self):
        HabilitationRequestFactory(organisation=self.org_a)
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Demandes d’habilitation en cours",
            response_content,
            "Confirmation message should be displayed.",
        )

    def test_add_aidant_allows_create_aidants_for_all_possible_organisations(self):
        self.client.force_login(self.responsable_tom)
        for organisation in self.responsable_tom.responsable_de.all():
            with transaction.atomic():
                self.responsable_tom.organisation = organisation
                self.responsable_tom.save()

            email = f"angela.dubois{organisation.id}@a.org"
            organisation_url = "/espace-responsable/organisation/"

            response = self.client.post(
                self.add_aidant_url,
                data={
                    "organisation": organisation.id,
                    "first_name": "Angela",
                    "last_name": "Dubois",
                    "email": email,
                    "profession": "Assistante sociale",
                },
            )
            self.assertRedirects(
                response, organisation_url, fetch_redirect_response=False
            )
            response = self.client.get(organisation_url)
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "La requête d’habilitation pour Angela Dubois a bien été enregistrée.",
                response_content,
                "Confirmation message should be displayed.",
            )
            self.assertIn(
                email,
                response_content,
                "New habilitation request should be displayed on organisation page.",
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

    def test_email_is_lowercased(self):
        self.client.force_login(self.responsable_tom)
        uppercased_email = "Angela.DUBOIS@doe.du"
        lowercased_email = "angela.dubois@doe.du"

        self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_a.id,
                "first_name": "Angela",
                "last_name": "Dubois",
                "email": uppercased_email,
                "profession": "Assistante sociale",
            },
        )

        last_request = HabilitationRequest.objects.last()
        self.assertEqual(last_request.email, lowercased_email)

    def test_submit_habilitation_request_for_same_email_and_organisation(self):
        self.client.force_login(self.responsable_tom)

        HabilitationRequestFactory(organisation=self.org_a, email="a@a.fr")

        response = self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_a.id,
                "email": "a@a.fr",
                "first_name": "Angela",
                "last_name": "Dubois",
                "profession": "Assistante sociale",
            },
        )
        self.assertEqual(response.status_code, 200, "Response should not be redirected")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Une demande d’habilitation est déjà en cours",
            response_content,
            "Error message should be displayed.",
        )

    def test_submit_habilitation_request_for_same_email_and_sister_organisation(self):
        self.client.force_login(self.responsable_tom)

        HabilitationRequestFactory(organisation=self.org_a, email="b@b.fr")

        response = self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_b.id,
                "email": "b@b.fr",
                "first_name": "Bob",
                "last_name": "Dubois",
                "profession": "Assistant social",
            },
        )
        self.assertEqual(response.status_code, 200, "Response should not be redirected")
        self.assertIn(
            "Une demande d’habilitation est déjà en cours",
            response.context_data["form"].errors["email"][0],
            "Error message should be displayed.",
        )

    def test_submitting_habilitation_request_if_aidant_already_exists(self):
        self.client.force_login(self.responsable_tom)

        existing_aidant = AidantFactory(organisation=self.org_a)

        response = self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_b.id,
                "email": existing_aidant.email,
                "first_name": "Bob",
                "last_name": "Dubois",
                "profession": "Assistant social",
            },
        )
        self.assertEqual(response.status_code, 200, "Response should not be redirected")
        self.assertIn(
            "Il existe déjà un compte aidant",
            response.context_data["form"].errors["email"][0],
            "Error message should be displayed.",
        )

    def test_avoid_oracle_for_other_organisations_requests(self):
        self.client.force_login(self.responsable_tom)

        HabilitationRequestFactory(organisation=OrganisationFactory(), email="b@b.fr")

        response = self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_a.id,
                "email": "b@b.fr",
                "first_name": "Bob",
                "last_name": "Dubois",
                "profession": "Assistant social",
            },
        )
        self.assertRedirects(
            response, self.organisation_url, fetch_redirect_response=False
        )
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "La requête d’habilitation pour Bob Dubois a bien été enregistrée.",
            response_content,
            "Confirmation message should be displayed.",
        )
        self.assertIn(
            "b@b.fr",
            response_content,
            "New habilitation request should be displayed on organisation page.",
        )

    def test_avoid_oracle_for_other_organisations_aidants(self):
        self.client.force_login(self.responsable_tom)

        other_aidant = AidantFactory()

        response = self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_a.id,
                "email": other_aidant.email,
                "first_name": "Bob",
                "last_name": "Dubois",
                "profession": "Assistant social",
            },
        )
        self.assertRedirects(
            response, self.organisation_url, fetch_redirect_response=False
        )
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "La requête d’habilitation pour Bob Dubois a bien été enregistrée.",
            response_content,
            "Confirmation message should be displayed.",
        )
        self.assertIn(
            other_aidant.email,
            response_content,
            "New habilitation request should be displayed on organisation page.",
        )


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
                "espace_responsable_register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )
        self.assertEqual(found.func.view_class, FormationRegistrationView)

    def test_renders_correct_template(self):
        self.client.force_login(self.referent)
        response = self.client.get(
            reverse(
                "espace_responsable_register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )
        self.assertTemplateUsed(response, "formation/formation-registration.html")

    def avoid_oracle(self):
        self.client.force_login(self.unrelated_referent)
        response = resolve(
            reverse(
                "espace_responsable_register_formation",
                kwargs={"request_id": self.habilitation_processing.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_cant_register_aidant_in_incorrect_state(self):
        self.client.force_login(self.referent)
        response = self.client.get(
            reverse(
                "espace_responsable_register_formation",
                kwargs={"request_id": self.habilitation_waiting.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_display_only_available_formations(self):
        self.client.force_login(self.referent)
        # Formation too close or already full should not be listed on the page
        response = self.client.get(
            reverse(
                "espace_responsable_register_formation",
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
                "espace_responsable_register_formation",
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
                "espace_responsable_register_formation",
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
                "espace_responsable_register_formation",
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
                "espace_responsable_register_formation",
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
