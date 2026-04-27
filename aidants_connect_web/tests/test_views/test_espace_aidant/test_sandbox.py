from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from aidants_connect_web.tests.factories import AidantFactory


@tag("aidants")
class EspaceAidantSandboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("espace_aidant:switch_main_organisation")
        cls.home_url = reverse("espace_aidant:home")
        cls.client = Client()
        cls.aidant = AidantFactory()

    def test_get_url(self):
        self.assertEqual(reverse("sandbox_presentation"), "/bac-a-sable/presentation")
