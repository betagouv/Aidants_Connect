from unittest import mock

from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_common.utils.constants import RequestStatusConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory
from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import AidantFactory, CarteTOTPFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class ValidateCarteTOTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Create one référent
        cls.responsable_tom = AidantFactory(username="tom@tom.fr")
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        # Create one aidant
        cls.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        # Create one carte TOTP
        cls.carte = CarteTOTPFactory(
            serial_number="A123", seed="FA169F10A9", aidant=cls.aidant_tim
        )

        cls.carte_resposable_tom = CarteTOTPFactory(
            serial_number="A456", seed="FA169F10A9", aidant=cls.responsable_tom
        )

        cls.org_id = cls.responsable_tom.organisation.id
        # Create one TOTP Device
        cls.device = TOTPDevice(
            tolerance=30, key=cls.carte.seed, user=cls.aidant_tim, step=60
        )

        cls.device_responsable = TOTPDevice(
            tolerance=30,
            key=cls.carte_resposable_tom.seed,
            user=cls.responsable_tom,
            step=60,
        )

        cls.device.save()
        cls.device_responsable.save()
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
        self.assertEqual(found.func, espace_responsable.validate_aidant_carte_totp)

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
        totp_device = TOTPDevice.objects.first()
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
