from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from aidants_connect_web.models import HabilitationRequest
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class HabilitationRequestsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Tom is responsable of organisations A and B
        cls.responsable_tom = AidantFactory()
        cls.org_a = cls.responsable_tom.organisation
        cls.org_b = OrganisationFactory(name="B")
        cls.responsable_tom.responsable_de.add(cls.org_a)
        cls.responsable_tom.responsable_de.add(cls.org_b)
        cls.responsable_tom.can_create_mandats = False
        # URL
        cls.add_aidant_url = (
            f"/espace-responsable/organisation/{cls.org_a.id}" "/aidant/ajouter/"
        )
        cls.organisation_url = f"/espace-responsable/organisation/{cls.org_a.id}/"

    def test_add_aidant_triggers_the_right_view(self):
        found = resolve(self.add_aidant_url)
        self.assertEqual(found.func, espace_responsable.new_habilitation_request)

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
            email = f"angela.dubois{organisation.id}@a.org"
            organisation_url = f"/espace-responsable/organisation/{organisation.id}/"

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
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Une demande d’habilitation est déjà en cours",
            response_content,
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
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Il existe déjà un compte aidant",
            response_content,
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
