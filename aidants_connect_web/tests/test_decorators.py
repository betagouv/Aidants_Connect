from django.conf import settings
from django.test import tag, TestCase
from django.utils import timezone

from freezegun import freeze_time

from aidants_connect_web.tests.factories import AidantFactory


fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("decorators")
class ActivityRequiredTests(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory()
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")

    def test_activity_required_decorated_page_loads_if_action_just_happened(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertEqual(response.status_code, 200)

    def test_activity_required_decorated_page_redirects_if_action_didnt_just_happened(
        self,
    ):
        self.client.force_login(self.aidant_thierry)
        with freeze_time(timezone.now() + settings.ACTIVITY_CHECK_DURATION):
            self.assertEqual(self.aidant_thierry.is_authenticated, True)
            response = self.client.get("/creation_mandat/")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/activity_check/?next=/creation_mandat/")


@tag("decorators")
class AidantRequiredTests(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory()
        self.responsable_georges = AidantFactory(
            username="georges@georges.com",
            organisation=self.aidant_thierry.organisation,
            can_create_mandats=False,
        )
        self.responsable_georges.responsable_de.add(self.aidant_thierry.organisation)

    def test_aidant_user_can_access_decorated_page(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertEqual(response.status_code, 200)

    def test_non_aidant_user_cannot_access_decorated_page(self):
        self.client.force_login(self.responsable_georges)
        response = self.client.get("/creation_mandat/")
        self.assertEqual(response.status_code, 302)
