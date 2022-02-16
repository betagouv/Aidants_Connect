from unittest.mock import patch
from uuid import UUID, uuid4

from django.forms import model_to_dict
from django.http import HttpResponse
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from factory import Faker
from faker.config import DEFAULT_LOCALE

from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    DataPrivacyOfficerForm,
    IssuerForm,
    ManagerForm,
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
class NewIssuerFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_issuer"
        cls.template_name = "issuer_form.html"

    def test_template(self):
        response = self.client.get(reverse(self.pattern_name))
        self.assertTemplateUsed(response, self.template_name)

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
class ModifyIssuerFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_modify_issuer"
        cls.template_name = "issuer_form.html"
        cls.issuer: Issuer = IssuerFactory()

    def test_404_on_bad_issuer_id(self):
        response = self.client.get(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid4()})
        )
        self.assertEqual(response.status_code, 404)

        form = utils.get_form(IssuerForm)
        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid4()}),
            form.clean(),
        )
        self.assertEqual(response.status_code, 404)

    def test_template(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id},
            )
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_on_correct_issuer_id_post_updates_model(self):
        new_name = Faker("first_name").evaluate(None, None, {"locale": DEFAULT_LOCALE})
        form = IssuerForm(data={**model_to_dict(self.issuer), "first_name": new_name})

        if not form.is_valid():
            raise ValueError(str(form.errors))

        self.assertNotEqual(self.issuer.first_name, new_name)

        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": self.issuer.issuer_id}),
            form.clean(),
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_organisation",
                kwargs={"issuer_id": self.issuer.issuer_id},
            ),
        )

        self.issuer.refresh_from_db()
        self.assertEqual(
            self.issuer.first_name,
            new_name,
            "The model's first_name field wasn't modified",
        )


@tag("habilitation")
class NewOrganisationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_organisation"
        cls.template_name = "organisation_form.html"
        cls.issuer: Issuer = IssuerFactory()

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

    def test_template(self):
        response = self.client.get(
            reverse(self.pattern_name, kwargs={"issuer_id": self.issuer.issuer_id})
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_redirect_valid_post_to_new_aidants(self):
        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id},
            ),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "draft_id": self.issuer.organisation_requests.first().draft_id,
                },
            ),
        )


@tag("habilitation")
class ModifyOrganisationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_modify_organisation"
        cls.template_name = "organisation_form.html"
        cls.issuer: Issuer = IssuerFactory()
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(
            draft_id=uuid4()
        )

    def test_404_on_bad_issuer_id(self):
        issuer_id = uuid4()

        response: HttpResponse = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": issuer_id, "draft_id": self.organisation.draft_id},
            )
        )
        self.assertEqual(response.status_code, 404)

        draft_id = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": draft_id,
                },
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_draft_id(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id, "draft_id": uuid4()},
            )
        )
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id, "draft_id": uuid4()},
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_template(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": self.organisation.draft_id,
                },
            )
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_on_correct_issuer_id_post_updates_model(self):
        model: OrganisationRequest = OrganisationRequestFactory(
            issuer=self.issuer, draft_id=uuid4()
        )
        new_name = Faker("company").evaluate(None, None, {"locale": DEFAULT_LOCALE})
        form = OrganisationRequestForm(data={**model_to_dict(model), "name": new_name})

        if not form.is_valid():
            raise ValueError(str(form.errors))

        cleaned_data = form.clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        self.assertNotEqual(model.name, new_name)

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": model.issuer.issuer_id,
                    "draft_id": model.draft_id,
                },
            ),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": model.issuer.issuer_id,
                    "draft_id": model.draft_id,
                },
            ),
        )

        model.refresh_from_db()
        self.assertEqual(model.name, new_name, "The model's name field wasn't modified")


@tag("habilitation")
class AidantsRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_aidants"
        cls.template_name = "personnel_form.html"
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(
            draft_id=uuid4()
        )

    def test_404_on_bad_issuer_id(self):
        issuer_id = uuid4()

        response: HttpResponse = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": issuer_id, "draft_id": self.organisation.draft_id},
            )
        )
        self.assertEqual(response.status_code, 404)

        draft_id = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": draft_id,
                },
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_draft_id(self):
        issuer: Issuer = IssuerFactory()

        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": issuer.issuer_id, "draft_id": uuid4()},
            )
        )
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": issuer.issuer_id, "draft_id": uuid4()},
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_template(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": self.organisation.draft_id,
                },
            )
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_redirect_valid_post_to_validation(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(draft_id=uuid4())

        manager_data = utils.get_form(ManagerForm).data
        dpo_data = utils.get_form(DataPrivacyOfficerForm).data
        aidants_data = utils.get_form(AidantRequestFormSet).data

        # Logic to manually put prefix on form data
        # See https://docs.djangoproject.com/fr/4.0/ref/forms/api/#django.forms.Form.prefix # noqa:E501
        cleaned_data = {
            **{f"manager-{k}": v for k, v in manager_data.items()},
            **{f"dpo-{k}": v for k, v in dpo_data.items()},
            **{k.replace("form-", "aidants-"): v for k, v in aidants_data.items()},
        }

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

        self.assertRedirects(
            response,
            reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "draft_id": str(organisation.draft_id),
                },
            ),
        )


@tag("habilitation")
class ValidationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_validation"
        cls.template_name = "validation_form.html"
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(
            draft_id=uuid4()
        )

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

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": organisation.issuer.issuer_id,
                    "draft_id": draft_id,
                },
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_draft_id(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": uuid4(),
                },
            )
        )
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": uuid4(),
                },
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_template(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": self.organisation.draft_id,
                },
            )
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_redirect_valid_post_to_new_issuer(self):
        cleaned_data = {
            "cgu": True,
            "dpo": True,
            "professionals_only": True,
            "without_elected": True,
        }

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "draft_id": self.organisation.draft_id,
                },
            ),
            cleaned_data,
        )

        self.assertRedirects(response, reverse("habilitation_new_issuer"))

    def test_post_invalid_data(self):
        valid_data = {
            "cgu": True,
            "dpo": True,
            "professionals_only": True,
            "without_elected": True,
        }

        for item in valid_data.keys():
            invalid_data = valid_data.copy()
            invalid_data[item] = False

            response = self.client.post(
                reverse(
                    self.pattern_name,
                    kwargs={
                        "issuer_id": self.organisation.issuer.issuer_id,
                        "draft_id": self.organisation.draft_id,
                    },
                ),
                invalid_data,
            )

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertIn(
                "Ce champ est obligatoire",
                str(response.context_data["form"].errors[item]),
            )
