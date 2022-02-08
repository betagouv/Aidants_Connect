from django.test import TestCase, override_settings

from django_otp.forms import OTPAuthenticationForm

from django_otp.plugins.otp_static.models import StaticToken

from aidants_connect_web.tests.factories import AidantFactory


@override_settings(ACTIVATE_INFINITY_TOKEN=True)
class InfiniteTokenAuthFormTest(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory(username="thierry@example.com")
        device = self.aidant_thierry.staticdevice_set.create(id=self.aidant_thierry.id)
        device.token_set.create(token="123456")

    def test_infinite_token(self):
        data = {
            "username": "thierry@example.com",
            "password": "motdepassedethierry",
            "otp_token": "123456",
        }
        form = OTPAuthenticationForm(None, data)
        self.assertTrue(form.is_valid())
        thierry = form.get_user()
        self.assertEqual(thierry, self.aidant_thierry)
        self.assertIsNotNone(thierry.otp_device)
        self.assertEqual(1, StaticToken.objects.all().count())

        other_form = OTPAuthenticationForm(None, data)
        self.assertTrue(other_form.is_valid())
