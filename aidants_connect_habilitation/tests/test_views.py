from datetime import timedelta
from unittest.mock import ANY, Mock, patch
from uuid import UUID, uuid4

from django.contrib import messages as django_messages
from django.core import mail
from django.forms import model_to_dict
from django.http import HttpResponse
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from factory import Faker
from faker.config import DEFAULT_LOCALE

from aidants_connect import settings
from aidants_connect.common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
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
    AidantRequestFactory,
    DraftOrganisationRequestFactory,
    IssuerFactory,
    ManagerFactory,
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

    @patch("aidants_connect_habilitation.views.send_mail")
    def test_send_email_when_issuer_already_exists(self, send_mail_mock: Mock):
        issuer: Issuer = IssuerFactory()

        data = utils.get_form(IssuerForm).clean()
        data["email"] = issuer.email

        self.client.post(reverse(self.pattern_name), data)

        send_mail_mock.assert_called_with(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=[issuer.email],
            subject=settings.EMAIL_HABILITATION_ISSUER_EMAIL_ALREADY_EXISTS_SUBJECT,
            message=ANY,
            html_message=ANY,
        )

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
        organisation = DraftOrganisationRequestFactory(issuer=self.issuer)
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        self.assertContains(response, RequestStatusConstants.NEW.value)
        self.assertContains(response, "Soumettre la demande")
        self.assertContains(response, organisation.name)

    def test_submitted_organisation_request_is_displayed_without_links(self):
        organisation = OrganisationRequestFactory(
            issuer=self.issuer,
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )
        response = self.client.get(self.get_url(self.issuer.issuer_id))
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
        cleaned_data = utils.get_form(
            OrganisationRequestForm, type_id=RequestOriginConstants.MEDIATHEQUE.value
        ).clean()
        cleaned_data["type"] = cleaned_data["type"].id
        cleaned_data.pop("is_private_org")
        cleaned_data.pop("france_services_label")

        response = self.client.post(
            reverse(
                self.pattern_name,
                kwargs={"issuer_id": self.issuer.issuer_id},
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
        new_name = Faker("company").evaluate(None, None, {"locale": DEFAULT_LOCALE})
        form = OrganisationRequestForm(data={**model_to_dict(model), "name": new_name})

        if not form.is_valid():
            raise ValueError(str(form.errors))

        cleaned_data = form.clean()
        cleaned_data["type"] = cleaned_data["type"].id

        # it is not enough to set these keys to False,
        # we need to unset them from the POST as they are checkboxes in the form.
        cleaned_data.pop("is_private_org")
        cleaned_data.pop("france_services_label")

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
# Run test with address searching disabled
@override_settings(GOUV_ADDRESS_SEARCH_API_DISABLED=True)
class AidantsRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_new_aidants"
        cls.template_name = "personnel_form.html"
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

        manager_data = utils.get_form(ManagerForm).data
        aidants_data = utils.get_form(AidantRequestFormSet).data

        # Logic to manually put prefix on form data
        # See https://docs.djangoproject.com/fr/4.0/ref/forms/api/#django.forms.Form.prefix # noqa:E501
        cleaned_data = {
            **{f"manager-{k}": v for k, v in manager_data.items()},
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
class ValidationRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_validation"
        cls.template_name = "validation_form.html"
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
        # expected button count = 5 -> issuer, org, more info, manager, aidant
        self.assertContains(response, "Éditer", 5)

    def test_do_the_job_and_redirect_valid_post_to_org_view(self):
        self.assertIsNone(self.organisation.data_pass_id)
        self.assertEqual(len(mail.outbox), 0)

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
            RequestStatusConstants.CHANGES_DONE.name,
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
            "Veuillez ajouter le responsable de la structure avant validation.",
            str(response.context_data["form"].errors),
        )

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

    def test_redirect_on_changes_done_organisation_request(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.CHANGES_DONE.name
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
        self.assertTemplateUsed(response, self.template_name)
        self.assertNotContains(response, "Éditer")

    def test_no_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, organisation.name)
        self.assertContains(
            response, RequestStatusConstants.AC_VALIDATION_PROCESSING.value
        )

    def test_issuer_can_post_a_message(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertNotContains(response, "Bonjour bonjour")
        self.client.post(
            organisation.get_absolute_url(), {"content": "Bonjour bonjour"}
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertContains(response, "Bonjour bonjour")

    def test_correct_message_is_shown_when_empty_messages_history(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertContains(response, "Notre conversation démarre ici.")
        self.client.post(
            organisation.get_absolute_url(), {"content": "Bonjour bonjour"}
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertNotContains(response, "Notre conversation démarre ici.")

    def shows_mofication_button_when_changes_required(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.CHANGES_REQUIRED.name
        )
        response = self.client.get(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid)
        )
        self.assertContains(response, "modify-btn")

    def not_show_mofication_button_when_other_status(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        response = self.client.get(
            self.get_url(organisation.issuer.issuer_id, organisation.uuid)
        )
        self.assertNotContains(response, "modify-btn")


class TestAddAidantsRequestView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_organisation_add_aidants"

    def test_redirects_on_unauthorized_request_status(self):
        unauthorized_statuses = set(RequestStatusConstants.values()) - {
            RequestStatusConstants.NEW.name,
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
            RequestStatusConstants.VALIDATED.name,
            RequestStatusConstants.CHANGES_DONE.name,
        }

        for i, status in enumerate(unauthorized_statuses):
            organisation: OrganisationRequest = OrganisationRequestFactory(
                status=status
            )

            response = self.client.get(
                self.__get_url(organisation.issuer.issuer_id, organisation.uuid)
            )

            self.assertRedirects(
                response,
                self.__get_redirect_url(
                    organisation.issuer.issuer_id, organisation.uuid
                ),
            )
            messages = list(django_messages.get_messages(response.wsgi_request))
            self.assertEqual(len(messages), i + 1)
            self.assertEqual(
                messages[i].message,
                "Il n'est pas possible d'ajouter de nouveaux aidants à cette demande.",
            )

    def __get_url(self, issuer_id, uuid):
        return reverse(
            self.pattern_name,
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )

    def __get_redirect_url(self, issuer_id, uuid):
        return reverse(
            "habilitation_organisation_view",
            kwargs={
                "issuer_id": issuer_id,
                "uuid": uuid,
            },
        )
