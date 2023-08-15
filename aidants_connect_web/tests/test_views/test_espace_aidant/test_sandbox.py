from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from aidants_connect_web.tests.factories import AidantFactory


@tag("aidants")
class EspaceAidantSandboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = "/espace-aidant/organisations/switch_main"
        cls.home_url = "/espace-aidant/"
        cls.client = Client()
        cls.aidant = AidantFactory()

    def test_get_url(self):
        self.assertEqual(reverse("sandbox_presentation"), "/bac-a-sable/presentation")

    def test_sandbox_presentation_view(self):
        self.client.force_login(self.aidant)
        response = self.client.get(self.home_url)
        self.assertContains(response, "bac-a-sable/presentation")
