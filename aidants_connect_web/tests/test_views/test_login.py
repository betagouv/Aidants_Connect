from django.core import mail
from django.test import TestCase, tag
from django.urls import reverse

from magicauth import settings as magicauth_settings

from aidants_connect_web.tests.factories import AidantFactory


@tag("usagers")
class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant = AidantFactory(is_active=False, post__with_otp_device=True)

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
