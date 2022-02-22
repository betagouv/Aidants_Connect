from django.test import TestCase, override_settings

from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory

from .admin import add_static_token_for_aidants


@override_settings(ACTIVATE_INFINITY_TOKEN=True)
class AdminAddInfiniteTokenTest(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory(username="thierry@example.com")

    def test_add_infinite_token(self):
        self.assertEqual(0, StaticDevice.objects.all().count())
        self.assertEqual(0, StaticToken.objects.all().count())
        for i in range(2):
            add_static_token_for_aidants(None, None, Aidant.objects.all())
            self.assertEqual(1, StaticDevice.objects.all().count())
            self.assertEqual(1, StaticToken.objects.all().count())
            self.assertEqual(
                1, StaticDevice.objects.filter(user=self.aidant_thierry).count()
            )
            self.assertEqual(
                1, StaticToken.objects.filter(device__user=self.aidant_thierry).count()
            )
