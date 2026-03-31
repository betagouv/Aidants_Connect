from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_static.models import StaticDevice

from aidants_connect_pico_cms.models import FaqQuestion, MandateTranslation, Testimony
from aidants_connect_web.tests.factories import AidantFactory


@tag("admin")
class VisibilityAdminPageTests(TestCase):
    amac_models = [
        Testimony,
        FaqQuestion,
        MandateTranslation,
    ]

    @classmethod
    def setUpTestData(cls):
        cls.amac_user = AidantFactory(
            is_staff=True,
            is_superuser=False,
        )
        cls.amac_user.set_password("password")
        cls.amac_user.save()
        amac_device = StaticDevice.objects.create(user=cls.amac_user, name="Device")

        cls.amac_client = Client()
        cls.amac_client.force_login(cls.amac_user)
        # we need do this :
        # https://docs.djangoproject.com/en/3.1/topics/testing/tools/#django.test.Client.session
        amac_session = cls.amac_client.session
        amac_session[DEVICE_ID_SESSION_KEY] = amac_device.persistent_id
        amac_session.save()

    def test_views_visible_by_amac_were_visible_by_amac_users(self):
        for model in self.amac_models:
            url_root = f"otpadmin:{model._meta.app_label}_{model.__name__.lower()}"
            list_url = reverse(url_root + "_changelist")
            response = self.amac_client.get(list_url)
            self.assertEqual(response.status_code, 200)
