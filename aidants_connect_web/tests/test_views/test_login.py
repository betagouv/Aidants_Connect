from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings, tag
from django.urls import reverse

from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from magicauth import settings as magicauth_settings

from aidants_connect_web.tests.factories import AidantFactory


@tag("usagers")
class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant = AidantFactory(
            is_active=False,
            post__with_otp_device=True,
            post__with_carte_totp=True,
        )
        cls.aidant_with_totp_card = AidantFactory(post__with_carte_totp=True)

    def test_inactive_aidant_with_valid_totp_cannot_login(self):
        response = self.client.post(
            "/accounts/login/", {"email": self.aidant.email, "otp_token": "123456"}
        )
        self.assertEqual(response.status_code, 200)
        # Check explicit message is displayed
        self.assertContains(
            response, "Votre compte existe mais il n’est pas encore actif."
        )
        # Check no email was sent
        self.assertEqual(len(mail.outbox), 0)

    def test_magicauth_login_redirects(self):
        response = self.client.get(f"/{magicauth_settings.LOGIN_URL}")

        self.assertRedirects(response, reverse("login"), status_code=301)

    # Prevent being throttled between test attemps
    @override_settings(OTP_TOTP_THROTTLE_FACTOR=0)
    def test_tolerance_on_otp_challenge(self):
        totp_device: TOTPDevice = self.aidant_with_totp_card.carte_totp.totp_device
        token_generator = TOTP(
            totp_device.bin_key,
            totp_device.step,
            totp_device.t0,
            totp_device.digits,
            totp_device.drift,
        )

        def login_and_assert(token, tolerance=1):
            response = self.client.post(
                "/accounts/login/",
                {"email": self.aidant_with_totp_card.email, "otp_token": token},
            )

            self.assertEqual(200, response.status_code)
            totp_device.refresh_from_db()
            self.assertEqual(tolerance, totp_device.tolerance)

        login_and_assert(token_generator.token() + 1, 1)
        login_and_assert(token_generator.token() + 1, 1)
        login_and_assert(
            token_generator.token() + 1, settings.DRIFTED_OTP_CARD_TOLERANCE
        )

        # Login with correct token
        response = self.client.post(
            "/accounts/login/",
            {
                "email": self.aidant_with_totp_card.email,
                "otp_token": token_generator.token(),
            },
        )

        self.assertEqual(302, response.status_code)
        # Simulate proper login
        self.client.force_login(self.aidant_with_totp_card)
        totp_device.refresh_from_db()
        self.assertEqual(1, totp_device.tolerance)
