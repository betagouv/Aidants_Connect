from unittest import mock

from django.contrib import messages as django_messages
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory
from aidants_connect_web.models import Aidant, Journal
from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class ValidateCarteTOTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Create one référent
        cls.responsable_tom = AidantFactory(
            username="tom@tom.fr",
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=True,
        )
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        # Create one aidant
        cls.aidant_tim: Aidant = AidantFactory(
            username="tim@tim.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=False,
        )

        cls.deactivated_aidant: Aidant = AidantFactory(
            username="deactivated@deactivated.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Deactivated",
            last_name="Onier",
            is_active=False,
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=False,
        )

        cls.org_id = cls.responsable_tom.organisation.id

        cls.organisation_url = f"/espace-responsable/organisation/{cls.org_id}"
        cls.aidant_url = f"/espace-responsable/aidant/{cls.aidant_tim.id}/"
        cls.responsable_url = f"/espace-responsable/aidant/{cls.responsable_tom.id}/"
        cls.validation_url = (
            f"/espace-responsable/aidant/{cls.aidant_tim.id}/valider-carte"
        )
        cls.validation_url_responsable = (
            f"/espace-responsable/aidant/{cls.responsable_tom.id}/valider-carte"
        )

    def test_validation_page_triggers_the_right_view(self):
        found = resolve(self.validation_url)
        self.assertEqual(
            found.func.view_class, espace_responsable.ValidateAidantCarteTOTP
        )

    def test_validation_page_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.validation_url)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/validate-carte-totp.html"
        )

    def test_validation_totp_with_valid_token(self):
        self.client.force_login(self.responsable_tom)

        with mock.patch("django_otp.oath.TOTP.verify", return_value=True):
            # Submit post and check redirection is correct
            response = self.client.post(
                self.validation_url,
                data={"otp_token": str(888888)},
            )
            self.assertRedirects(
                response, self.aidant_url, fetch_redirect_response=False
            )

        # Check TOTP device is correct
        self.aidant_tim.refresh_from_db()
        totp_device = self.aidant_tim.carte_totp.totp_device
        self.assertTrue(
            totp_device.confirmed, "Validated TOTP Device should be confirmed"
        )
        self.assertLess(
            totp_device.tolerance,
            30,
            "Validated TOTP Device should have a decreased tolerance",
        )
        # Check journal entry creation
        journal_entry = Journal.objects.last()
        self.assertEqual(
            journal_entry.action,
            "card_validation",
            "A Journal entry should have been created on card validation.",
        )

        # Check organisation page does not warn about activation
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "Le fonctionnement de cette carte n'a pas été vérifié.",
            response_content,
            "Organization page should display a warning about activation.",
        )

    def test_validation_manager_totp_closes_open_requests(self):
        self.client.force_login(self.responsable_tom)

        # create validated request
        OrganisationRequestFactory(
            status=RequestStatusConstants.VALIDATED.name,
            organisation=self.responsable_tom.organisation,
        )

        with mock.patch("django_otp.oath.TOTP.verify", return_value=True):
            # Submit post and check redirection is correct
            response = self.client.post(
                self.validation_url_responsable,
                data={"otp_token": str(888888)},
            )
            self.assertRedirects(
                response, self.responsable_url, fetch_redirect_response=False
            )

        # verify if request was updated
        valid_organisation_requests = OrganisationRequest.objects.filter(
            organisation__in=self.responsable_tom.responsable_de.all()
        )

        self.assertEqual(
            valid_organisation_requests[0].status, RequestStatusConstants.CLOSED.name
        )

    def test_validation_totp_with_invalid_token(self):
        self.client.force_login(self.responsable_tom)

        with mock.patch("django_otp.oath.TOTP.verify", return_value=False):
            # Submit post and check there is no redirection
            response = self.client.post(
                self.validation_url,
                data={"otp_token": str(999999)},
            )
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "Ce code n’est pas valide.",
                response_content,
                "Form should warn if the code is not valid.",
            )

    def test_redirect_if_aidant_is_deactivated(self):
        self.client.force_login(self.responsable_tom)

        self.assertFalse(self.deactivated_aidant.carte_totp.totp_device.confirmed)

        response = self.client.post(
            reverse(
                "espace_responsable_validate_totp",
                kwargs={"aidant_id": self.deactivated_aidant.pk},
            ),
            data={"serial_number": self.deactivated_aidant.carte_totp.serial_number},
        )
        self.assertRedirects(
            response,
            reverse(
                "espace_responsable_aidant",
                kwargs={"aidant_id": self.deactivated_aidant.id},
            ),
        )
        self.deactivated_aidant.refresh_from_db()
        self.assertFalse(self.deactivated_aidant.carte_totp.totp_device.confirmed)

        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            f"Erreur : le profil de {self.deactivated_aidant.get_full_name()} "
            "est désactivé. "
            "Il est impossible de valider la carte Aidants Connect qui lui est "
            "associée.",
            messages[0].message,
        )
