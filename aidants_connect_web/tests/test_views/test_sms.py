from django.test import TestCase, tag
from django.urls import resolve, reverse

from aidants_connect_web.views import sms


@tag("sms")
class CallbackTests(TestCase):
    def test_sms_callback_url_triggers_the_correct_view(self):
        found = resolve(reverse("sms_callback"))
        self.assertEqual(found.func.view_class, sms.Callback)

    def test__check_user_consents(self):
        target = sms.Callback()
        self.assertTrue(target._check_user_consents("Oui"))
        self.assertTrue(target._check_user_consents("  Oui  "))
        self.assertTrue(target._check_user_consents("  Oui  ."))
        self.assertTrue(target._check_user_consents("  Oui  .  "))
        self.assertFalse(target._check_user_consents("Oui;"))
        self.assertFalse(target._check_user_consents("Oui non"))
