from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import TOTP

from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class ValidateCarteTOTPTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create one responsable
        self.responsable_tom = AidantFactory(username="tom@tom.fr")
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)
        # Create one aidant
        self.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=self.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        # Create one carte TOTP
        self.carte = CarteTOTPFactory(
            serial_number="A123", seed="FA169F10A9", aidant=self.aidant_tim
        )
        self.org_id = self.responsable_tom.organisation.id
        # Create one TOTP Device
        self.device = TOTPDevice(
            tolerance=30, key=self.carte.seed, user=self.aidant_tim, step=60
        )
        self.device.save()
        self.organisation_url = f"/espace-responsable/organisation/{self.org_id}/"
        self.validation_url = (
            f"/espace-responsable/organisation/{self.org_id}/"
            f"aidant/{self.aidant_tim.id}/valider-carte"
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

        # Generate a valid TOTP token
        totp = TOTP(
            self.device.bin_key,
            self.device.step,
            self.device.t0,
            self.device.digits,
            self.device.drift,
        )
        valid_token = totp.token()

        # Submit post and check redirection is correct
        response = self.client.post(
            self.validation_url,
            data={"otp_token": str(valid_token)},
        )
        self.assertRedirects(
            response, self.organisation_url, fetch_redirect_response=False
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

        # Check organisation page does not warn about activation
        response = self.client.get(self.organisation_url)
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "Le fonctionnement de cette carte n'a pas été vérifié.",
            response_content,
            "Organization page should display a warning about activation.",
        )

    def test_validation_totp_with_invalid_token(self):
        self.client.force_login(self.responsable_tom)

        # Generate an invalid TOTP token
        invalid_token = 999999

        # Submit post and check there is no redirection
        response = self.client.post(
            self.validation_url,
            data={"otp_token": str(invalid_token)},
        )
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Ce code n’est pas valide.",
            response_content,
            "Form should warn if the code is not valid.",
        )
