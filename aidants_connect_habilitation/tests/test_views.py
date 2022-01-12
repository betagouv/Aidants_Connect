from unittest.mock import patch
from uuid import UUID, uuid4

from django.http import HttpResponse
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    IssuerForm,
    OrganisationRequestForm,
)
from aidants_connect_habilitation.models import Issuer, OrganisationRequest
from aidants_connect_habilitation.tests import utils
from aidants_connect_habilitation.tests.factories import (
    IssuerFactory,
    OrganisationRequestFactory,
)


@tag("habilitation")
class NewHabilitationViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

    def test_redirect(self):
        response = self.client.get(reverse("habilitation_new"))
        self.assertRedirects(
            response, reverse("habilitation_new_issuer"), status_code=301
        )


@tag("habilitation")
class IssuerFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_issuer"

    def test_template(self):
        response = self.client.get(reverse(self.pattern_name))
        self.assertTemplateUsed(response, "issuer_form.html")

    def test_redirect_valid_post_to_new_organisation(self):
        temp_uuid = "d6cc0622-b525-41ee-a8dc-c65de9536dba"

        with patch(
            "aidants_connect_habilitation.models.uuid4",
            return_value=UUID(temp_uuid),
        ):
            form = utils.get_form(IssuerForm)
            response = self.client.post(reverse(self.pattern_name), form.clean())

            self.assertRedirects(
                response,
                reverse(
                    "habilitation_new_organisation",
                    kwargs={"issuer_id": temp_uuid},
                ),
            )


@tag("habilitation")
class OrganisationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_organisation"

    def test_404_on_bad_issuer_id(self):
        uuid = uuid4()

        response: HttpResponse = self.client.get(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid})
        )
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response: HttpResponse = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid}), cleaned_data
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_valid_post_to_new_aidants(self):
        issuer: Issuer = IssuerFactory()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": issuer.issuer_id},
            ),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": issuer.issuer_id,
                    "draft_id": issuer.organisation_requests.first().draft_id,
                },
            ),
        )


@tag("habilitation")
class AidantsRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_aidants"

    def test_404_on_bad_issuer_id(self):
        issuer_id = uuid4()

        organisation: OrganisationRequest = OrganisationRequestFactory(draft_id=uuid4())

        response: HttpResponse = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": issuer_id, "draft_id": organisation.draft_id},
            )
        )
        self.assertEqual(response.status_code, 404)

        draft_id = uuid4()
        while OrganisationRequest.objects.filter(draft_id=draft_id).exists():
            draft_id = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response: HttpResponse = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": organisation.issuer_id, "draft_id": draft_id},
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_valid_post_to_new_issuer(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(draft_id=uuid4())
        cleaned_data = utils.get_form(AidantRequestFormSet).data

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": organisation.issuer.issuer_id,
                    "draft_id": organisation.draft_id,
                },
            ),
            cleaned_data,
        )

        self.assertRedirects(response, reverse("habilitation_new_issuer"))
