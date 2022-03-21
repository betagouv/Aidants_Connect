from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from django.forms import model_to_dict
from django.http import HttpResponse
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from factory import Faker
from faker.config import DEFAULT_LOCALE

from aidants_connect import settings
from aidants_connect.common.constants import RequestStatusConstants
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    DataPrivacyOfficerForm,
    IssuerForm,
    ManagerForm,
    OrganisationRequestForm,
)
from aidants_connect_habilitation.models import (
    Issuer,
    IssuerEmailConfirmation,
    OrganisationRequest,
)
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

    def test_redirect_valid_post_to_email_confirmation_wait(self):
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
                    "habilitation_issuer_email_confirmation_waiting",
                    kwargs={"issuer_id": temp_uuid},
                ),
            )

    def test_redirect_valid_post_creates_an_email_confirmation(self):
        temp_uuid = "d6cc0622-b525-41ee-a8dc-c65de9536dba"

        with patch(
            "aidants_connect_habilitation.models.uuid4",
            return_value=UUID(temp_uuid),
        ):
            with self.assertRaises(IssuerEmailConfirmation.DoesNotExist):
                IssuerEmailConfirmation.objects.get(issuer__issuer_id=temp_uuid)

            form = utils.get_form(IssuerForm)
            self.client.post(reverse(self.pattern_name), form.clean())

            try:
                IssuerEmailConfirmation.objects.get(issuer__issuer_id=temp_uuid)
            except IssuerEmailConfirmation.DoesNotExist:
                self.fail(
                    "Request should have created an instance of IssuerEmailConfirmation"
                )


@tag("habilitation")
class IssuerEmailConfirmationWaitingViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_issuer_email_confirmation_waiting"
        cls.template_name = "email_confirmation_waiting.html"
        cls.issuer: Issuer = IssuerFactory(email_verified=False)

    def test_404_on_bad_issuer_id(self):
        response = self.client.get(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid4()})
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

    def test_post_create_email_confirmation(self):
        with self.assertRaises(IssuerEmailConfirmation.DoesNotExist):
            IssuerEmailConfirmation.objects.get(issuer=self.issuer)

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id},
            )
        )
        self.assertTemplateUsed(response, self.template_name)

        try:
            IssuerEmailConfirmation.objects.get(issuer=self.issuer)
        except IssuerEmailConfirmation.DoesNotExist:
            self.fail(
                "Request should have created an instance of IssuerEmailConfirmation"
            )


@tag("habilitation")
class IssuerEmailConfirmationViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_issuer_email_confirmation_confirm"
        cls.template_name = "email_confirmation_confirm.html"
        cls.issuer: Issuer = IssuerFactory(email_verified=False)
        cls.email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=cls.issuer, sent=now()
        )
        cls.expired_email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=cls.issuer,
            sent=now() - timedelta(days=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS + 2),
        )

    def test_404_on_bad_issuer_id(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": uuid4(), "key": get_random_string(64).lower()},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_no_email_confirmation(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "key": get_random_string(64).lower(),
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_unrelated_issuer_confirmation(self):
        unrelated_issuer: Issuer = IssuerFactory(email_verified=False)
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": unrelated_issuer.issuer_id,
                    "key": self.email_confirmation.key,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_template(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "key": self.email_confirmation.key,
                },
            )
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_get_redirect_on_previously_confirmed(self):
        confirmed_issuer: Issuer = IssuerFactory(email_verified=True)
        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=confirmed_issuer, sent=now()
        )
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": confirmed_issuer.issuer_id,
                    "key": email_confirmation.key,
                },
            )
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_organisation",
                kwargs={"issuer_id": confirmed_issuer.issuer_id},
            ),
        )

    def test_post_confirms_email(self):
        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "key": self.email_confirmation.key,
                },
            )
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_organisation",
                kwargs={"issuer_id": self.issuer.issuer_id},
            ),
        )

    def test_fails_on_expired_key(self):
        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "key": self.expired_email_confirmation.key,
                },
            )
        )
        self.assertTemplateUsed(response, self.template_name)


@tag("habilitation")
class IssuerPageViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_issuer_page"
        cls.template_name = "issuer_space.html"
        cls.issuer: Issuer = IssuerFactory()

    def get_url(self, issuer_id):
        return reverse(self.pattern_name, kwargs={"issuer_id": issuer_id})

    def test_good_template_is_used(self):
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        self.assertTemplateUsed(response, self.template_name)

    def test_404_on_bad_issuer_id(self):
        response = self.client.get(self.get_url(uuid4()))
        self.assertEqual(response.status_code, 404)

    def test_new_organisation_request_is_displayed_with_links(self):
        organisation = OrganisationRequestFactory(
            issuer=self.issuer, uuid=uuid4(), status=RequestStatusConstants.NEW.name
        )
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        print(response.content)
        self.assertContains(response, RequestStatusConstants.NEW.value)
        self.assertContains(response, "Soumettre la demande")
        self.assertContains(response, organisation.name)

    def test_submitted_organisation_request_is_displayed_without_links(self):
        organisation = OrganisationRequestFactory(
            issuer=self.issuer,
            uuid=uuid4(),
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        print(response.content)
        self.assertNotContains(response, RequestStatusConstants.NEW.value)
        self.assertContains(
            response, RequestStatusConstants.AC_VALIDATION_PROCESSING.value
        )
        self.assertNotContains(response, "Soumettre la demande")
        self.assertContains(response, organisation.name)


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

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        response = self.client.get(
            reverse(
                self.pattern_name, kwargs={"issuer_id": unverified_issuer.issuer_id}
            )
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

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

        self.assertNotEqual(self.issuer.first_name, new_name)

        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": self.issuer.issuer_id}),
            {**model_to_dict(self.issuer), "first_name": new_name},
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

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        response = self.client.get(
            reverse(
                self.pattern_name, kwargs={"issuer_id": unverified_issuer.issuer_id}
            )
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

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
                    "uuid": self.issuer.organisation_requests.first().uuid,
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
            uuid=uuid4(),
            issuer=cls.issuer,
            status=RequestStatusConstants.NEW.name,
        )

    def get_url(self, issuer_id, uuid):
        return reverse(
            self.pattern_name,
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )

    def test_404_on_bad_issuer_id(self):
        issuer_id = uuid4()

        response: HttpResponse = self.client.get(
            self.get_url(issuer_id, self.organisation.uuid)
        )
        self.assertEqual(response.status_code, 404)

        uuid = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            self.get_url(self.organisation.issuer.issuer_id, uuid),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_uuid(self):
        response = self.client.get(self.get_url(self.issuer.issuer_id, uuid4()))
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            self.get_url(self.issuer.issuer_id, uuid4()),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        organisation = OrganisationRequestFactory(
            issuer=unverified_issuer, uuid=uuid4()
        )
        response = self.client.get(
            self.get_url(unverified_issuer.issuer_id, organisation.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

    def test_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            uuid=uuid4(),
            issuer=self.issuer,
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        response = self.client.get(
            self.get_url(self.issuer.issuer_id, organisation.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_organisation_view",
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "uuid": organisation.uuid,
                },
            ),
        )

    def test_template(self):
        response = self.client.get(
            self.get_url(self.issuer.issuer_id, self.organisation.uuid)
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_on_correct_issuer_id_post_updates_model(self):
        model: OrganisationRequest = OrganisationRequestFactory(
            issuer=self.issuer, uuid=uuid4(), status=RequestStatusConstants.NEW.name
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
            self.get_url(model.issuer.issuer_id, model.uuid),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": model.issuer.issuer_id,
                    "uuid": model.uuid,
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
            uuid=uuid4(), status=RequestStatusConstants.NEW.name
        )

    def get_url(self, issuer_id, uuid):
        return reverse(
            self.pattern_name,
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )

    def test_404_on_bad_issuer_id(self):
        issuer_id = uuid4()

        response: HttpResponse = self.client.get(
            self.get_url(issuer_id, self.organisation.uuid)
        )
        self.assertEqual(response.status_code, 404)

        uuid = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            self.get_url(self.organisation.issuer.issuer_id, uuid),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_unrelated_issuer_id(self):
        unrelated_issuer = IssuerFactory()

        response: HttpResponse = self.client.get(
            self.get_url(unrelated_issuer.issuer_id, self.organisation.uuid)
        )
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            self.get_url(unrelated_issuer.issuer_id, self.organisation.uuid),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_uuid(self):
        issuer: Issuer = IssuerFactory()

        response = self.client.get(self.get_url(issuer.issuer_id, uuid4()))
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            self.get_url(issuer.issuer_id, uuid4()),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        organisation = OrganisationRequestFactory(
            issuer=unverified_issuer, uuid=uuid4()
        )
        response = self.client.get(
            self.get_url(unverified_issuer.issuer_id, organisation.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

    def test_template(self):
        response = self.client.get(
            self.get_url(self.organisation.issuer.issuer_id, self.organisation.uuid)
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_redirect_valid_post_to_validation(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(uuid=uuid4())

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
            self.get_url(organisation.issuer.issuer_id, organisation.uuid),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            ),
        )

    def test_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            uuid=uuid4(),
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        response = self.client.get(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_organisation_view",
                kwargs={
                    "issuer_id": organisation.issuer.issuer_id,
                    "uuid": organisation.uuid,
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
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(uuid=uuid4())

    def get_url(self, issuer_id, uuid):
        return reverse(
            self.pattern_name,
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )

    def test_404_on_bad_issuer_id(self):
        issuer_id = uuid4()

        organisation: OrganisationRequest = OrganisationRequestFactory(uuid=uuid4())

        response: HttpResponse = self.client.get(
            self.get_url(issuer_id, organisation.uuid)
        )
        self.assertEqual(response.status_code, 404)

        uuid = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["public_service_delegation_attestation"] = ""
        response = self.client.post(
            self.get_url(organisation.issuer.issuer_id, uuid),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_uuid(self):
        response = self.client.get(
            self.get_url(self.organisation.issuer.issuer_id, uuid4())
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
                    "uuid": uuid4(),
                },
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        organisation_request = OrganisationRequestFactory(
            issuer=unverified_issuer, uuid=uuid4()
        )
        response = self.client.get(
            self.get_url(unverified_issuer.issuer_id, organisation_request.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

    def test_template(self):
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.organisation.issuer.issuer_id,
                    "uuid": self.organisation.uuid,
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
            self.get_url(self.organisation.issuer.issuer_id, self.organisation.uuid),
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
                self.get_url(
                    self.organisation.issuer.issuer_id, self.organisation.uuid
                ),
                invalid_data,
            )

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertIn(
                "Ce champ est obligatoire",
                str(response.context_data["form"].errors[item]),
            )

    def test_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            uuid=uuid4(),
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        response = self.client.get(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_organisation_view",
                kwargs={
                    "issuer_id": organisation.issuer.issuer_id,
                    "uuid": organisation.uuid,
                },
            ),
        )


@tag("habilitation")
class RequestReadOnlyViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_organisation_view"
        cls.template_name = "view_organisation_request.html"
        cls.issuer = IssuerFactory()
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(
            uuid=uuid4(),
            issuer=cls.issuer,
        )

    def get_url(self, issuer_id, uuid):
        return reverse(
            self.pattern_name,
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )

    def test_404_on_bad_issuer_id(self):
        response: HttpResponse = self.client.get(
            self.get_url(uuid4(), self.organisation.uuid)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_uuid(self):
        response = self.client.get(self.get_url(self.issuer.issuer_id, uuid4()))
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        organisation = OrganisationRequestFactory(
            issuer=unverified_issuer, uuid=uuid4()
        )
        response = self.client.get(
            self.get_url(unverified_issuer.issuer_id, organisation.uuid)
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

    def test_right_template_is_used(self):
        response = self.client.get(
            self.get_url(self.organisation.issuer.issuer_id, self.organisation.uuid)
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_no_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            draft_id=uuid4(),
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        response = self.client.get(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, organisation.name)
        self.assertContains(
            response, RequestStatusConstants.AC_VALIDATION_PROCESSING.value
        )
