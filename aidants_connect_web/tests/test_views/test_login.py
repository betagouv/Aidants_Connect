from unittest import mock
from unittest.mock import Mock

from django.core import mail
from django.test import TestCase, override_settings, tag
from django.urls import reverse

from django_otp.plugins.otp_totp.models import TOTPDevice
from magicauth import settings as magicauth_settings

from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.views.login import tld_need_another_stmp


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

    @override_settings(TDL_NEED_BACKUP_SMTP="laposte.net")
    def test_tld_need_another_stmp_with_one_tld(self):
        self.assertTrue(tld_need_another_stmp("sophie@laposte.net"))
        self.assertTrue(tld_need_another_stmp("sophie@dupont@laposte.net"))
        self.assertFalse(tld_need_another_stmp("mario@nintendo.net"))

    @override_settings(TDL_NEED_BACKUP_SMTP="laposte.net,tdlbis.com")
    def test_tld_need_another_stmp_with_two_tld(self):
        self.assertTrue(tld_need_another_stmp("sophie@laposte.net"))
        self.assertTrue(tld_need_another_stmp("peach@tdlbis.com"))
        self.assertFalse(tld_need_another_stmp("mario@nintendo.net"))

    def test_inactive_aidant_with_valid_totp_cannot_login(self):
        response = self.client.post(
            reverse("login"), {"email": self.aidant.email, "otp_token": "123456"}
        )
        self.assertEqual(response.status_code, 200)
        # Check explicit message is displayed
        self.assertContains(response, "Erreur : votre compte a été désactivé.")
        # Check no email was sent
        self.assertEqual(len(mail.outbox), 0)

    def test_magicauth_login_redirects(self):
        response = self.client.get(f"/{magicauth_settings.LOGIN_URL}")
        self.assertRedirects(response, reverse("login"), status_code=301)

    @override_settings(MAGICAUTH_ENABLE_2FA=True)
    @mock.patch("magicauth.views.OTPForm.is_valid")
    def test_tolerance_on_otp_challenge(self, is_valid_mock: Mock):
        totp_device: TOTPDevice = self.aidant_with_totp_card.carte_totp.totp_device

        is_valid_mock.return_value = False

        response = self.client.post(
            reverse("login"),
            {
                "email": self.aidant_with_totp_card.email,
                "otp_token": 123456,
            },
        )

        self.assertEqual(200, response.status_code)
        totp_device.refresh_from_db()
        self.assertEqual(10, totp_device.tolerance)

        # Simulate too many failed connection attempts
        totp_device.throttling_failure_count = 3
        totp_device.save()

        response = self.client.post(
            reverse("login"),
            {
                "email": self.aidant_with_totp_card.email,
                "otp_token": 123456,
            },
        )

        self.assertEqual(200, response.status_code)
        totp_device.refresh_from_db()
        self.assertEqual(30, totp_device.tolerance)

        # Login with correct token
        is_valid_mock.return_value = True
        response = self.client.post(
            reverse("login"),
            {
                "email": self.aidant_with_totp_card.email,
                "otp_token": 123456,
            },
        )

        self.assertEqual(302, response.status_code)
        # Simulate proper login
        self.client.force_login(self.aidant_with_totp_card)
        totp_device.refresh_from_db()
        self.assertEqual(1, totp_device.tolerance)
