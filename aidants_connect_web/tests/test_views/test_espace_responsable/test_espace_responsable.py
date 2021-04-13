from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from aidants_connect_web.tests.factories import (
    AidantFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class EspaceResponsableHomePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.responsable_tom = AidantFactory(username="georges@plop.net")
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)

    def test_anonymous_user_cannot_access_espace_aidant_view(self):
        response = self.client.get("/espace-responsable/")
        self.assertRedirects(response, "/accounts/login/?next=/espace-responsable/")

    def test_espace_aidant_home_url_triggers_the_right_view(self):
        found = resolve("/espace-responsable/")
        self.assertEqual(found.func, espace_responsable.home)

    def test_espace_aidant_home_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get("/espace-responsable/")
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/home.html"
        )
