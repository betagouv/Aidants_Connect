from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from django.core import mail
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from faker import Faker

from aidants_connect import settings
from aidants_connect_common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_common.models import Formation
from aidants_connect_common.tests.factories import (
    FormationFactory,
    FormationOrganizationFactory,
)
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    EmailOrganisationValidationError,
    IssuerForm,
    OrganisationRequestForm,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    IssuerEmailConfirmation,
    OrganisationRequest,
)
from aidants_connect_habilitation.tests import utils
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    DraftOrganisationRequestFactory,
    IssuerFactory,
    ManagerFactory,
    OrganisationRequestFactory,
)
from aidants_connect_habilitation.views import (
    AidantFormationRegistrationView,
    HabilitationRequestCancelationView,
)
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.tests.factories import HabilitationRequestFactory


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

    def test_send_email_when_issuer_already_exists(self):
        issuer: Issuer = IssuerFactory()

        data = utils.get_form(IssuerForm).clean()
        data["email"] = issuer.email

        self.assertEqual(0, len(mail.outbox))

        self.client.post(reverse(self.pattern_name), data)

        self.assertEqual(1, len(mail.outbox))
        self.assertEqual([issuer.email.casefold()], mail.outbox[0].to)

        data["email"] = issuer.email.capitalize()

        self.assertNotEqual(issuer.email, data["email"])

        self.client.post(reverse(self.pattern_name), data)

        self.assertEqual(2, len(mail.outbox))
        self.assertEqual([issuer.email.casefold()], mail.outbox[1].to)

    def test_render_warning_when_issuer_already_exists(self):
        issuer: Issuer = IssuerFactory()

        data = utils.get_form(IssuerForm).clean()
        data["email"] = issuer.email

        response = self.client.post(reverse(self.pattern_name), data)

        self.assertTemplateUsed(response, "issuer_already_exists_warning.html")


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

    def test_post_redirects_to_new_organisation(self):
        confirmed_issuer: Issuer = IssuerFactory(email_verified=True)
        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=confirmed_issuer, sent=now()
        )
        response = self.client.post(
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
                "habilitation_siret_verification",
                kwargs={"issuer_id": confirmed_issuer.issuer_id},
            ),
        )

    def test_get_confirms_email(self):
        self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": self.issuer.issuer_id,
                    "key": self.email_confirmation.key,
                },
            )
        )
        issuer = Issuer.objects.get(issuer_id=self.issuer.issuer_id)
        self.assertTrue(issuer.email_verified)

    def test_fails_on_expired_key(self):
        response = self.client.get(
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
        organisation = DraftOrganisationRequestFactory(issuer=self.issuer)
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        self.assertContains(response, RequestStatusConstants.NEW.label)
        self.assertContains(response, organisation.name)

    def test_submitted_organisation_request_is_displayed_without_links(self):
        organisation = OrganisationRequestFactory(
            issuer=self.issuer,
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.value,
        )
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        self.assertNotContains(response, RequestStatusConstants.NEW.value)
        self.assertContains(response, "En attente")
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
        new_name = Faker().first_name()

        self.assertNotEqual(self.issuer.first_name, new_name)

        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": self.issuer.issuer_id}),
            {**model_to_dict(self.issuer), "first_name": new_name},
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_siret_verification",
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
        cls.pattern_name = "habilitation_new_organisation"
        cls.template_name = "aidants_connect_habilitation/organisation-form-view.html"
        cls.issuer: Issuer = IssuerFactory()

    def test_404_on_bad_issuer_id(self):
        uuid = uuid4()

        response: HttpResponse = self.client.get(
            reverse(
                self.pattern_name, kwargs={"issuer_id": uuid, "siret": "12345678901234"}
            )
        )
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        response: HttpResponse = self.client.post(
            reverse(
                self.pattern_name, kwargs={"issuer_id": uuid, "siret": "12345678901234"}
            ),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        response = self.client.get(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": unverified_issuer.issuer_id,
                    "siret": "12345678901234",
                },
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
                kwargs={"issuer_id": self.issuer.issuer_id, "siret": "12345678901234"},
            )
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_redirect_valid_post_to_new_aidants(self):
        cleaned_data = utils.get_form(
            OrganisationRequestForm, type_id=RequestOriginConstants.MEDIATHEQUE.value
        ).clean()
        cleaned_data["type"] = cleaned_data["type"].id
        cleaned_data.pop("france_services_label")

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id, "siret": "12345678901234"},
            ),
            cleaned_data,
        )

        self.assertTrue(
            OrganisationRequest.objects.filter(issuer=self.issuer).exists(),
            "No organisationrequest was created in DB",
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_referent",
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
        cls.pattern_name = "habilitation_modify_organisation"
        cls.template_name = "aidants_connect_habilitation/organisation-form-view.html"
        cls.issuer: Issuer = IssuerFactory()
        cls.organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=cls.issuer
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
        response = self.client.post(
            self.get_url(self.organisation.issuer.issuer_id, uuid),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_bad_uuid(self):
        response = self.client.get(self.get_url(self.issuer.issuer_id, uuid4()))
        self.assertEqual(response.status_code, 404)

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            self.get_url(self.issuer.issuer_id, uuid4()),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        organisation = DraftOrganisationRequestFactory(issuer=unverified_issuer)
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
        model: OrganisationRequest = DraftOrganisationRequestFactory(issuer=self.issuer)
        new_name = Faker().company()
        form = OrganisationRequestForm(data={**model_to_dict(model), "name": new_name})

        if not form.is_valid():
            raise ValueError(str(form.errors))

        cleaned_data = form.clean()
        cleaned_data["type"] = cleaned_data["type"].id

        # it is not enough to set these keys to False,
        # we need to unset them from the POST as they are checkboxes in the form.
        cleaned_data.pop("france_services_label")

        self.assertNotEqual(model.name, new_name)

        response = self.client.post(
            self.get_url(model.issuer.issuer_id, model.uuid),
            cleaned_data,
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_referent",
                kwargs={
                    "issuer_id": model.issuer.issuer_id,
                    "uuid": model.uuid,
                },
            ),
        )

        model.refresh_from_db()
        self.assertEqual(model.name, new_name, "The model's name field wasn't modified")


@tag("habilitation")
class PersonnelRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.template_name = "aidants_connect_habilitation/personnel-form-view.html"
        cls.issuer: Issuer = IssuerFactory()
        cls.organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            issuer=cls.issuer
        )

    def test_template(self):
        response = self.client.get(
            self.__get_url(self.issuer.issuer_id, self.organisation.uuid)
        )
        self.assertTemplateUsed(response, self.template_name)

    def test_has_errors_on_aidants_with_same_email(self):
        aidants_email = Faker().email()

        aidants_data = utils.get_form(
            AidantRequestFormSet,
            ignore_errors=True,
            form_init_kwargs={
                "organisation": self.organisation,
                "initial": 2,
            },
            email=aidants_email,
        ).data

        response = self.client.post(
            self.__get_url(self.issuer.issuer_id, self.organisation.uuid),
            data=aidants_data,
        )

        self.assertTemplateUsed(response, self.template_name)

        self.assertIn(
            str(EmailOrganisationValidationError(aidants_email)),
            str(response.context_data["form"].forms[0].errors["email"].data),
        )

        self.assertFalse(response.context_data["form"].is_valid())

        aidant: AidantRequest = AidantRequestFactory(organisation=self.organisation)

        aidants_data = utils.get_form(
            AidantRequestFormSet,
            ignore_errors=True,
            form_init_kwargs={"organisation": self.organisation, "initial": 1},
            email=aidant.email,
        ).data

        response = self.client.post(
            self.__get_url(self.issuer.issuer_id, self.organisation.uuid),
            data=aidants_data,
        )

        self.assertTemplateUsed(response, self.template_name)

        self.assertIn(
            str(EmailOrganisationValidationError(aidant.email)),
            str(response.context_data["form"].forms[0].errors["email"].data),
        )

        self.assertFalse(response.context_data["form"].is_valid())

    def __get_url(self, issuer_id, uuid):
        return reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )


@tag("habilitation")
# Run test with address searching disabled
@override_settings(GOUV_ADDRESS_SEARCH_API_DISABLED=True)
class AidantsRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_aidants"
        cls.template_name = "aidants_connect_habilitation/personnel-form-view.html"
        cls.organisation: OrganisationRequest = DraftOrganisationRequestFactory()

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
        cleaned_data["type"] = cleaned_data["type"].id

        response = self.client.post(
            self.get_url(issuer.issuer_id, uuid4()),
            cleaned_data,
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        organisation = OrganisationRequestFactory(issuer=unverified_issuer)
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
        organisation: OrganisationRequest = DraftOrganisationRequestFactory()

        aidants_data = utils.get_form(
            AidantRequestFormSet, form_init_kwargs={"organisation": organisation}
        ).data

        response = self.client.post(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid),
            aidants_data,
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


@tag("habilitation")
class ValidationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_validation"
        cls.template_name = "aidants_connect_habilitation/validation-request-form-view.html"  # noqa: E501
        cls.organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            manager=ManagerFactory()
        )
        AidantRequestFactory(organisation=cls.organisation)
        cls.organisation_no_manager: OrganisationRequest = (
            DraftOrganisationRequestFactory(manager=None)
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

        organisation: OrganisationRequest = OrganisationRequestFactory()

        response: HttpResponse = self.client.get(
            self.get_url(issuer_id, organisation.uuid)
        )
        self.assertEqual(response.status_code, 404)

        uuid = uuid4()

        cleaned_data = utils.get_form(OrganisationRequestForm).clean()
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
        organisation_request = OrganisationRequestFactory(issuer=unverified_issuer)
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
            self.get_url(self.organisation.issuer.issuer_id, self.organisation.uuid)
        )
        self.assertTemplateUsed(response, self.template_name)
        # expected button count = 4 -> issuer, org,, manager, aidant
        self.assertContains(
            response, f"/demandeur/{self.organisation.issuer.issuer_id}/modifier/"
        )
        self.assertContains(
            response,
            f"/demandeur/{self.organisation.issuer.issuer_id}/organisation/"
            f"{self.organisation.uuid}/infos-generales/",
        )
        self.assertContains(
            response,
            f"/demandeur/{self.organisation.issuer.issuer_id}/organisation/"
            f"{self.organisation.uuid}/referent/",
        )
        self.assertContains(
            response,
            f"/demandeur/{self.organisation.issuer.issuer_id}/organisation/"
            f"{self.organisation.uuid}/aidants/",
        )

    def test_do_the_job_and_redirect_valid_post_to_org_view(self):
        self.assertIsNone(self.organisation.data_pass_id)
        self.assertEqual(len(mail.outbox), 0)

        cleaned_data = {
            "cgu": True,
            "not_free": True,
            "dpo": True,
            "professionals_only": True,
            "without_elected": True,
        }

        response = self.client.post(
            self.get_url(self.organisation.issuer.issuer_id, self.organisation.uuid),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            self.organisation.get_absolute_url(),
        )
        self.organisation.refresh_from_db()
        self.assertIsNotNone(self.organisation.data_pass_id)

        self.assertEqual(
            self.organisation.status,
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        [
            self.assertTrue(getattr(self.organisation, name))
            for name in cleaned_data.keys()
        ]

        self.assertEqual(len(mail.outbox), 1)
        organisation_request_creation_message = mail.outbox[0]
        self.assertIn(
            "Aidants Connect - Votre demande d’habilitation a été soumise",
            organisation_request_creation_message.subject,
        )
        self.assertIn(
            str(self.organisation.name), organisation_request_creation_message.body
        )

    def test_do_the_job_when_changes_required(self):
        self.assertEqual(len(mail.outbox), 0)

        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.CHANGES_REQUIRED.name
        )
        data_pass_id = organisation.data_pass_id

        cleaned_data = {
            "cgu": True,
            "not_free": True,
            "dpo": True,
            "professionals_only": True,
            "without_elected": True,
        }

        response = self.client.post(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid),
            cleaned_data,
        )

        self.assertRedirects(
            response,
            organisation.get_absolute_url(),
        )
        organisation.refresh_from_db()
        self.assertEqual(data_pass_id, organisation.data_pass_id)
        self.assertEqual(
            organisation.status,
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )

        self.assertEqual(len(mail.outbox), 2)
        organisation_request_modification_message = mail.outbox[1]
        self.assertIn(
            "Aidants Connect - Votre demande d’habilitation a été modifiée",
            organisation_request_modification_message.subject,
        )
        self.assertIn(
            str(organisation.name), organisation_request_modification_message.body
        )

    def test_post_no_manager_raises_error(self):
        valid_data = {
            "cgu": True,
            "not_free": True,
            "dpo": True,
            "professionals_only": True,
            "without_elected": True,
        }
        response = self.client.post(
            self.get_url(
                self.organisation_no_manager.issuer.issuer_id,
                self.organisation_no_manager.uuid,
            ),
            valid_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn(
            "Veuillez ajouter le ou la référente de la structure avant validation.",
            str(response.context_data["form"].errors),
        )

    def test_post_invalid_data(self):
        valid_data = {
            "cgu": True,
            "not_free": True,
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
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
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
        cls.issuer = IssuerFactory()
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(
            issuer=cls.issuer
        )

        issuer = IssuerFactory()
        cls.orgs = [
            OrganisationRequestFactory(
                issuer=issuer, status=status, post__aidants_count=1
            )
            for status in RequestStatusConstants
        ]

        cls.do_not_add_aidants = OrganisationRequest.objects.filter(
            issuer=issuer,
            status__in=(
                set(RequestStatusConstants)
                - set(RequestStatusConstants.personel_editable)
            ),
        ).all()

        cls.do_add_aidants = OrganisationRequest.objects.filter(
            issuer=issuer, status__in=RequestStatusConstants.personel_editable
        ).all()

        cls.do_not_validate = OrganisationRequest.objects.filter(
            issuer=issuer,
            status__in=(
                set(RequestStatusConstants) - set(RequestStatusConstants.validatable)
            ),
        ).all()

        cls.do_validate = OrganisationRequest.objects.filter(
            issuer=issuer, status__in=RequestStatusConstants.validatable
        ).all()

        cls.do_edit_organisation = OrganisationRequest.objects.filter(
            issuer=issuer, status__in=RequestStatusConstants.organisation_editable
        ).all()

        cls.do_not_edit_organisation = OrganisationRequest.objects.filter(
            issuer=issuer,
            status__in=(
                set(RequestStatusConstants)
                - set(RequestStatusConstants.organisation_editable)
            ),
        ).all()

    def get_url(self, issuer_id, uuid):
        return reverse(
            "habilitation_organisation_view",
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
        organisation = OrganisationRequestFactory(issuer=unverified_issuer)
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
        self.assertTemplateUsed(
            response, "aidants_connect_habilitation/validation-request-form-view.html"
        )

    def test_no_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, organisation.name)
        self.assertContains(
            response, RequestStatusConstants.AC_VALIDATION_PROCESSING.label
        )

    def test_can_edit_organisation_in_right_circumstances(self):
        for organisation in self.do_edit_organisation:
            with self.subTest(f"Modifiable {organisation.status}"):
                response = self.client.get(
                    self.get_url(organisation.issuer.issuer_id, organisation.uuid)
                )

                self.assertContains(
                    response,
                    reverse(
                        "habilitation_modify_organisation",
                        kwargs={
                            "issuer_id": organisation.issuer.issuer_id,
                            "uuid": str(organisation.uuid),
                        },
                    ),
                )

        for organisation in self.do_not_edit_organisation:
            with self.subTest(f"Unmodifiable {organisation.status}"):
                response = self.client.get(
                    self.get_url(organisation.issuer.issuer_id, organisation.uuid)
                )

                self.assertNotContains(
                    response,
                    reverse(
                        "habilitation_modify_organisation",
                        kwargs={
                            "issuer_id": organisation.issuer.issuer_id,
                            "uuid": str(organisation.uuid),
                        },
                    ),
                )

    def test_not_show_mofication_button_when_other_status(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING
        )
        response = self.client.get(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid)
        )
        self.assertNotContains(response, "Modifier votre demande")

    def test_can_add_aidant_in_right_circumstances(self):
        text_to_search = "Ajouter un autre aidant à la demande"

        for organisation in self.do_not_add_aidants:
            response = self.client.get(
                self.get_url(organisation.issuer.issuer_id, organisation.uuid)
            )
            self.assertNotContains(response, text_to_search)

        for organisation in self.do_add_aidants:
            response = self.client.get(
                self.get_url(organisation.issuer.issuer_id, organisation.uuid)
            )
            self.assertContains(response, text_to_search)

    def test_can_modify_aidant_in_right_circumstances(self):
        for organisation in self.do_not_add_aidants:
            with self.subTest(f"Unmodifiable status: {organisation.status}"):
                response = self.client.get(
                    self.get_url(organisation.issuer.issuer_id, organisation.uuid)
                )
                self.assertNotContains(
                    response,
                    reverse(
                        "api_habilitation_aidant_edit",
                        kwargs={
                            "issuer_id": str(organisation.issuer.issuer_id),
                            "uuid": str(organisation.uuid),
                            "aidant_id": organisation.aidant_requests.first().pk,
                        },
                    ),
                )

        for organisation in self.do_add_aidants:
            with self.subTest(f"Modifiable status: {organisation.status}"):
                response = self.client.get(
                    self.get_url(organisation.issuer.issuer_id, organisation.uuid)
                )
                self.assertContains(
                    response,
                    reverse(
                        "api_habilitation_aidant_edit",
                        kwargs={
                            "issuer_id": str(organisation.issuer.issuer_id),
                            "uuid": str(organisation.uuid),
                            "aidant_id": organisation.aidant_requests.first().pk,
                        },
                    ),
                )

    def test_referent_formation_registration(self):
        with self.subTest(
            "Do not display formation registration button when manager is aidant"
        ):
            organisation = OrganisationRequestFactory(
                manager=ManagerFactory(is_aidant=True)
            )
            # Assert organisation has no registered aidant; we just want to test manager
            self.assertEqual(0, organisation.aidant_requests.count())

            response = self.client.get(
                self.get_url(organisation.issuer.issuer_id, organisation.uuid)
            )
            self.assertNotContains(response, "Inscrire en formation")
            self.assertNotContains(response, "Inscrit à la formation aidant")
            self.assertNotContains(response, reverse("espace_responsable_organisation"))
            self.assertNotContains(
                response,
                reverse(
                    "habilitation_manager_formation_registration",
                    kwargs={
                        "issuer_id": organisation.issuer.issuer_id,
                        "uuid": organisation.uuid,
                    },
                ),
            )

        with self.subTest("Display espace referent button"):
            with transaction.atomic():
                organisation: OrganisationRequest = OrganisationRequestFactory(
                    manager=ManagerFactory(
                        is_aidant=True,
                        habilitation_request=HabilitationRequestFactory(
                            status=ReferentRequestStatuses.STATUS_PROCESSING
                        ),
                    )
                )
                organisation.accept_request_and_create_organisation()
                organisation.manager.aidant.last_login = timezone.now()
                organisation.manager.aidant.save()

            # Assert organisation has no registered aidant; we just want to test manager
            self.assertEqual(0, organisation.aidant_requests.count())

            response = self.client.get(
                self.get_url(organisation.issuer.issuer_id, organisation.uuid)
            )
            self.assertContains(response, "Inscrire en formation")
            self.assertNotContains(response, "Inscrit à la formation aidant")
            self.assertContains(response, reverse("espace_responsable_organisation"))
            self.assertNotContains(
                response,
                reverse(
                    "habilitation_manager_formation_registration",
                    kwargs={
                        "issuer_id": organisation.issuer.issuer_id,
                        "uuid": organisation.uuid,
                    },
                ),
            )

        with self.subTest("Display formation button"):
            with transaction.atomic():
                organisation: OrganisationRequest = OrganisationRequestFactory(
                    manager=ManagerFactory(is_aidant=True)
                )
                organisation.accept_request_and_create_organisation()

            # Assert organisation has no registered aidant; we just want to test manager
            self.assertEqual(0, organisation.aidant_requests.count())

            response = self.client.get(
                self.get_url(organisation.issuer.issuer_id, organisation.uuid)
            )
            self.assertContains(response, "Inscrire en formation")
            self.assertNotContains(response, "Inscrit à la formation aidant")
            self.assertNotContains(response, reverse("espace_responsable_organisation"))
            self.assertContains(
                response,
                reverse(
                    "habilitation_manager_formation_registration",
                    kwargs={
                        "issuer_id": organisation.issuer.issuer_id,
                        "uuid": organisation.uuid,
                    },
                ),
            )

        with self.subTest("Is registered to formation"):
            with transaction.atomic():
                organisation: OrganisationRequest = OrganisationRequestFactory(
                    manager=ManagerFactory(is_aidant=True)
                )
                organisation.accept_request_and_create_organisation()
                FormationFactory(attendants=[organisation.manager.habilitation_request])

            # Assert organisation has no registered aidant; we just want to test manager
            self.assertEqual(0, organisation.aidant_requests.count())

            response = self.client.get(
                self.get_url(organisation.issuer.issuer_id, organisation.uuid)
            )
            self.assertContains(response, "Inscrire en formation")
            self.assertContains(response, "Inscrit à la formation aidant")
            self.assertNotContains(response, reverse("espace_responsable_organisation"))
            self.assertContains(
                response,
                reverse(
                    "habilitation_manager_formation_registration",
                    kwargs={
                        "issuer_id": organisation.issuer.issuer_id,
                        "uuid": organisation.uuid,
                    },
                ),
            )


class TestFormationRegistrationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unrelated_organisation = OrganisationRequestFactory()
        cls.unrelated_aidant1 = AidantRequestFactory(
            organisation=cls.unrelated_organisation
        )

        cls.organisation = OrganisationRequestFactory()

        hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION
        )
        cls.aidant_with_newly_created_habilitation: AidantRequestFactory = (
            AidantRequestFactory(
                organisation=cls.organisation, habilitation_request=hab
            )
        )

        hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_PROCESSING
        )
        cls.aidant_with_ongoing_habilitation: AidantRequest = AidantRequestFactory(
            organisation=cls.organisation, habilitation_request=hab
        )
        cls.aidant_without_habilitation: AidantRequestFactory = AidantRequestFactory(
            organisation=cls.organisation
        )

        cls.formation_ok: Formation = FormationFactory(
            type_label="Des formations et des Hommes",
            start_datetime=now() + timedelta(days=50),
            organisation=FormationOrganizationFactory(name="Organisation_Formation_OK"),
        )

        cls.formation_too_close: Formation = FormationFactory(
            type_label="À la Bonne Formation", start_datetime=now() + timedelta(days=1)
        )

        cls.formation_full: Formation = FormationFactory(
            type_label="A fond la Formation",
            start_datetime=now() + timedelta(days=50),
            max_attendants=1,
        )
        cls.formation_full.register_attendant(HabilitationRequestFactory())

        cls.aidant_registered_to_2_formations: AidantRequest = AidantRequestFactory(
            organisation=cls.organisation,
            habilitation_request=HabilitationRequestFactory(
                status=ReferentRequestStatuses.STATUS_PROCESSING
            ),
        )

        cls.formation_with_aidant1: Formation = FormationFactory(
            type_label="Hein? formations",
            start_datetime=now() + timedelta(days=46),
            attendants=[cls.aidant_registered_to_2_formations.habilitation_request],
            max_attendants=10,
        )

        cls.formation_with_aidant2: Formation = FormationFactory(
            type_label="Formes Ah Scions",
            start_datetime=now() + timedelta(days=46),
            attendants=[cls.aidant_registered_to_2_formations.habilitation_request],
            max_attendants=10,
        )

    def test_triggers_correct_view(self):
        found = resolve(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertEqual(found.func.view_class, AidantFormationRegistrationView)

    def test_renders_correct_template(self):
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertTemplateUsed(response, "formation/formation-registration.html")

    def test_cant_register_aidant_of_unrelated_request(self):
        # Issuer is unrelated
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.unrelated_organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_newly_created_habilitation.pk,
                },
            )
        )
        self.assertEqual(404, response.status_code)

        # Organisation is unrelated
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.unrelated_organisation.uuid),
                    "aidant_id": self.aidant_with_newly_created_habilitation.pk,
                },
            )
        )
        self.assertEqual(404, response.status_code)

        # Organisation and issuer are unrelated
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.unrelated_organisation.issuer.issuer_id),
                    "uuid": str(self.unrelated_organisation.uuid),
                    "aidant_id": self.aidant_with_newly_created_habilitation.pk,
                },
            )
        )
        self.assertEqual(404, response.status_code)

    def test_cant_register_aidant_in_incorrect_state(self):
        # AidantRequest object must have a related HabilitationRequest object
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.unrelated_organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_newly_created_habilitation.pk,
                },
            )
        )
        self.assertEqual(404, response.status_code)

        # Related HabilitationRequest object's status must be allowed
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.unrelated_organisation.issuer.issuer_id),
                    "uuid": str(self.unrelated_organisation.uuid),
                    "aidant_id": self.aidant_without_habilitation.pk,
                },
            )
        )
        self.assertEqual(404, response.status_code)

    def test_display_only_available_formations(self):
        # Formation too close or already full should not be listed on the page
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )

        self.assertIn(self.formation_ok.type.label, response.content.decode())
        self.assertIn(self.formation_ok.organisation.name, response.content.decode())
        self.assertNotIn(self.formation_too_close.type.label, response.content.decode())
        self.assertNotIn(self.formation_full.type.label, response.content.decode())

    def test_registration(self):
        self.assertEqual(0, self.formation_ok.attendants.count())
        response = self.client.post(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            ),
            data={"formations": [self.formation_full.pk]},
        )
        self.formation_ok.refresh_from_db()
        self.assertTemplateUsed(response, "formation/formation-registration.html")
        self.assertEqual(0, self.formation_ok.attendants.count())
        self.assertIn("formations", response.context_data["form"].errors)

        response = self.client.post(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            ),
            data={"formations": [self.formation_too_close.pk]},
        )
        self.formation_ok.refresh_from_db()
        self.assertTemplateUsed(response, "formation/formation-registration.html")
        self.assertEqual(0, self.formation_ok.attendants.count())
        self.assertIn("formations", response.context_data["form"].errors)

        self.client.post(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            ),
            data={"formations": [self.formation_ok.pk]},
        )
        self.formation_ok.refresh_from_db()
        self.assertEqual(
            {self.aidant_with_ongoing_habilitation.habilitation_request},
            {item.attendant for item in self.formation_ok.attendants.all()},
        )

    def test_unregistration(self):
        hab = self.aidant_registered_to_2_formations.habilitation_request
        self.assertEqual(
            {self.formation_with_aidant1, self.formation_with_aidant2},
            {fa.formation for fa in hab.formations.all()},
        )
        self.client.post(
            reverse(
                "habilitation_new_aidant_formation_registration",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_registered_to_2_formations.pk,
                },
            ),
            data={"formations": [self.formation_ok.pk, self.formation_with_aidant1.pk]},
        )
        hab = self.aidant_registered_to_2_formations.habilitation_request
        self.assertEqual(
            {self.formation_with_aidant1, self.formation_ok},
            {fa.formation for fa in hab.formations.all()},
        )


class TestHabilitationRequestCancelationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationRequestFactory()

        hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE
        )
        cls.aidant_with_cancelled_habilitation: AidantRequestFactory = (
            AidantRequestFactory(
                organisation=cls.organisation, habilitation_request=hab
            )
        )

        cls.aidant_without_habilitation: AidantRequestFactory = AidantRequestFactory(
            organisation=cls.organisation
        )

        hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_VALIDATED
        )
        cls.aidant_with_newly_validated_habilitation: AidantRequestFactory = (
            AidantRequestFactory(
                organisation=cls.organisation, habilitation_request=hab
            )
        )

        hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_PROCESSING
        )
        cls.aidant_with_ongoing_habilitation: AidantRequest = AidantRequestFactory(
            organisation=cls.organisation, habilitation_request=hab
        )

        hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_VALIDATED
        )
        cls.unrelated_aidant_request: AidantRequestFactory = AidantRequestFactory(
            habilitation_request=hab
        )

    def test_triggers_correct_view(self):
        found = resolve(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertEqual(found.func.view_class, HabilitationRequestCancelationView)

    def test_renders_correct_template(self):
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertTemplateUsed(response, "cancel-habilitation-request.html")

    def test_404_on_bad_url_parameters(self):
        response = self.client.get(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(uuid4()),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(uuid4()),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.unrelated_aidant_request.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_without_habilitation.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_cancelled_habilitation.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_cancel_habilitation(self):
        self.assertTrue(
            self.aidant_with_ongoing_habilitation.habilitation_request.status_cancellable_by_responsable  # noqa: E501
        )
        response = self.client.post(
            reverse(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                    "aidant_id": self.aidant_with_ongoing_habilitation.pk,
                },
            )
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_organisation_view",
                kwargs={
                    "issuer_id": str(self.organisation.issuer.issuer_id),
                    "uuid": str(self.organisation.uuid),
                },
            ),
        )
        self.aidant_with_ongoing_habilitation.habilitation_request.refresh_from_db()
        self.assertFalse(
            self.aidant_with_ongoing_habilitation.habilitation_request.status_cancellable_by_responsable  # noqa: E501
        )


@tag("habilitation")
class NewOrganisationSiretVerificationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_siret_verification"
        cls.template_name = "aidants_connect_habilitation/organisation-siret-verification-form-view.html"  # noqa: E501
        cls.issuer: Issuer = IssuerFactory()

    def test_404_on_bad_issuer_id(self):
        response = self.client.get(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid4()})
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


@tag("habilitation")
class NewOrganisationSiretNavigationViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_siret_navigation"
        cls.issuer: Issuer = IssuerFactory()

    def test_404_on_bad_issuer_id(self):
        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": uuid4()}),
            {"siret": "78866504300012", "organisation_choice": "0"},
        )
        self.assertEqual(response.status_code, 404)

    def test_redirect_on_unverified_issuer_email(self):
        unverified_issuer: Issuer = IssuerFactory(email_verified=False)
        response = self.client.post(
            reverse(
                self.pattern_name, kwargs={"issuer_id": unverified_issuer.issuer_id}
            ),
            {"siret": "78866504300012", "organisation_choice": "0"},
        )
        self.assertRedirects(
            response,
            reverse(
                "habilitation_issuer_email_confirmation_waiting",
                kwargs={"issuer_id": unverified_issuer.issuer_id},
            ),
        )

    def test_redirect_to_new_organisation_when_siret_new(self):
        siret = "78866504300012"
        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": self.issuer.issuer_id}),
            {"siret": siret, "organisation_choice": "0"},
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_new_organisation",
                kwargs={"issuer_id": self.issuer.issuer_id, "siret": siret},
            ),
        )

    def test_redirect_to_siret_verification_when_no_siret(self):
        response = self.client.post(
            reverse(self.pattern_name, kwargs={"issuer_id": self.issuer.issuer_id}), {}
        )

        self.assertRedirects(
            response,
            reverse(
                "habilitation_siret_verification",
                kwargs={"issuer_id": self.issuer.issuer_id},
            ),
        )
