from django.test.client import Client
from django.test import TestCase, tag
from django.urls import resolve

from aidants_connect_web.views import usagers
from aidants_connect_web.tests.factories import UserFactory, UsagerFactory


@tag("usagers")
class UsagersIndexPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = UserFactory()

    def test_usagers_index_url_triggers_the_usagers_index_view(self):
        found = resolve("/usagers/")
        self.assertEqual(found.func, usagers.usagers_index)

    def test_usagers_index_url_triggers_the_usagers_index_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/usagers/")
        self.assertTemplateUsed(response, "aidants_connect_web/usagers.html")


@tag("usagers")
class UsagersDetailsPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = UserFactory()
        self.usager = UsagerFactory()

    def test_usagers_details_url_triggers_the_usagers_details_view(self):
        found = resolve("/usagers/1/")
        self.assertEqual(found.func, usagers.usagers_details)
