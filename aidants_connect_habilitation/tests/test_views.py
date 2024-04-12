from datetime import timedelta
from unittest import skip
from unittest.mock import ANY, Mock, patch
from uuid import UUID, uuid4

from django.contrib import messages as django_messages
from django.core import mail
from django.forms import model_to_dict
from django.http import HttpResponse
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from faker import Faker

from aidants_connect import settings
from aidants_connect_common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_common.models import Formation
from aidants_connect_common.tests.factories import FormationFactory
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    EmailOrganisationValidationError,
    IssuerForm,
    ManagerForm,
    OrganisationRequestForm,
    PersonnelForm,
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
from aidants_connect_habilitation.tests.utils import get_form
from aidants_connect_habilitation.views import (
    AidantFormationRegistrationView,
    HabilitationRequestCancelationView,
)
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import HabilitationRequest, Organisation
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

        # Also test when user gives their email with capitals
        send_mail_mock.reset_mock()
        send_mail_mock.assert_not_called()

        data["email"] = issuer.email.capitalize()

        self.assertNotEqual(issuer.email, data["email"])

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
                "habilitation_new_organisation",
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
        self.assertContains(response, "Soumettre la demande")
        self.assertContains(response, organisation.name)

    def test_submitted_organisation_request_is_displayed_without_links(self):
        organisation = OrganisationRequestFactory(
            issuer=self.issuer,
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.value,
        )
        response = self.client.get(self.get_url(self.issuer.issuer_id))
        self.assertNotContains(response, RequestStatusConstants.NEW.value)
        self.assertContains(
            response, RequestStatusConstants.AC_VALIDATION_PROCESSING.label
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
        new_name = Faker().first_name()

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
        new_name = Faker().company()
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
class PersonnelRequestFormViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.template_name = "personnel_form.html"
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

        manager_data = utils.get_form(
            ManagerForm, form_init_kwargs={"prefix": PersonnelForm.MANAGER_FORM_PREFIX}
        ).data

        aidants_data = utils.get_form(
            AidantRequestFormSet,
            ignore_errors=True,
            form_init_kwargs={
                "organisation": self.organisation,
                "initial": 2,
                "prefix": PersonnelForm.AIDANTS_FORMSET_PREFIX,
            },
            email=aidants_email,
        ).data

        response = self.client.post(
            self.__get_url(self.issuer.issuer_id, self.organisation.uuid),
            data={**manager_data, **aidants_data},
        )

        self.assertTemplateUsed(response, self.template_name)

        self.assertIn(
            str(EmailOrganisationValidationError(aidants_email)),
            str(
                response.context_data["form"]
                .aidants_formset.forms[0]
                .errors["email"]
                .data
            ),
        )

        self.assertFalse(response.context_data["form"].is_valid())

        aidant: AidantRequest = AidantRequestFactory(organisation=self.organisation)

        manager_data = utils.get_form(
            ManagerForm, form_init_kwargs={"prefix": PersonnelForm.MANAGER_FORM_PREFIX}
        ).data

        aidants_data = utils.get_form(
            AidantRequestFormSet,
            ignore_errors=True,
            form_init_kwargs={
                "organisation": self.organisation,
                "initial": 1,
                "prefix": PersonnelForm.AIDANTS_FORMSET_PREFIX,
            },
            email=aidant.email,
        ).data

        response = self.client.post(
            self.__get_url(self.issuer.issuer_id, self.organisation.uuid),
            data={**manager_data, **aidants_data},
        )

        self.assertTemplateUsed(response, self.template_name)

        self.assertIn(
            str(EmailOrganisationValidationError(aidant.email)),
            str(
                response.context_data["form"]
                .aidants_formset.forms[0]
                .errors["email"]
                .data
            ),
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
        aidants_data = utils.get_form(
            AidantRequestFormSet, form_init_kwargs={"organisation": organisation}
        ).data

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
        self.assertNotContains(response, settings.SUPPORT_EMAIL)
        self.assertContains(response, settings.AC_CONTACT_EMAIL)
        self.assertNotContains(response, "Éditer")

    def test_no_redirect_on_confirmed_organisation_request(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.value
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, organisation.name)
        self.assertContains(
            response, RequestStatusConstants.AC_VALIDATION_PROCESSING.label
        )

    @skip
    def test_issuer_can_post_a_message(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.value
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertNotContains(response, "Bonjour bonjour")
        self.client.post(
            organisation.get_absolute_url(), {"content": "Bonjour bonjour"}
        )
        response = self.client.get(organisation.get_absolute_url())
        self.assertContains(response, "Bonjour bonjour")

    @skip
    def test_correct_message_is_shown_when_empty_messages_history(self):
        organisation = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.value
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


class AddAidantsRequestViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.pattern_name = "habilitation_organisation_add_aidants"

    def test_redirects_on_unauthorized_request_status(self):
        unauthorized_statuses = set(RequestStatusConstants.values) - {
            RequestStatusConstants.NEW.name,
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
            RequestStatusConstants.VALIDATED.name,
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

    def test_creates_aidants_when_request_is_validated(self):
        org_req: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
            manager=ManagerFactory(is_aidant=False),
        )
        [AidantRequestFactory(organisation=org_req) for _ in range(3)]

        # Create aidants_connect_web.models.Organisation &
        # aidants_connect_web.models.HabilitationRequest objects
        org_req.accept_request_and_create_organisation()
        org_req.refresh_from_db()

        organisation: Organisation = Organisation.objects.get(
            data_pass_id=org_req.data_pass_id
        )

        self.assertEqual(RequestStatusConstants.VALIDATED.name, org_req.status)
        self.assertEqual(
            3,
            HabilitationRequest.objects.filter(
                organisation=organisation,
                origin=HabilitationRequest.ORIGIN_HABILITATION,
            ).count(),
        )

        furthermore = get_form(
            AidantRequestFormSet,
            form_init_kwargs={"organisation": org_req, "initial": 3},
        ).data

        self.client.post(
            self.__get_url(org_req.issuer.issuer_id, org_req.uuid), furthermore
        )

        self.assertEqual(
            6, HabilitationRequest.objects.filter(organisation=organisation).count()
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
