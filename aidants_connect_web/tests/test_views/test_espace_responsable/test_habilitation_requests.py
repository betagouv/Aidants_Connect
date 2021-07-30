from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class EspaceResponsableHomePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Tom is responsable of organisations A and B
        cls.responsable_tom = AidantFactory(username="tom@baie.fr")
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

    def test_submitting_habilitation_request_nominal_case(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.post(
            self.add_aidant_url,
            data={
                "organisation": self.org_a.id,
                "first_name": "Angela",
                "last_name": "Dubois",
                "email": "angela.dubois@a.org",
                "profession": "Assistante sociale",
            },
        )
        self.assertRedirects(
            response, self.organisation_url, fetch_redirect_response=False
        )
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "La requête d’habilitation pour Angela Dubois a bien été enregistrée.",
            response_content,
            "Confirmation message should be displayed.",
        )
        self.assertIn(
            "angela.dubois@a.org",
            response_content,
            "New habilitation request should be displayed on organisation page.",
        )
