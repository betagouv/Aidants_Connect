from admin_honeypot.models import LoginAttempt

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class LoginAttemptAdminPageTests(TestCase):

    def test_honeypot_login_attempt_fails_gracefuly(self):
        login_attempt_id = LoginAttempt.objects.create(username="test").pk
        path = reverse('admin:admin_honeypot_loginattempt_change',
                       args=(login_attempt_id,))
        admin = settings.ADMIN_URL
        admin_url = f"/{admin}admin_honeypot/loginattempt/{login_attempt_id}/change/"
        self.assertEqual(admin_url, path)
