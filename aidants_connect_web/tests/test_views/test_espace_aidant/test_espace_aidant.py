from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.views import espace_aidant, usagers


@tag("usagers")
class EspaceAidantHomePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = AidantFactory()

    def test_anonymous_user_cannot_access_espace_aidant_view(self):
        response = self.client.get("/espace-aidant/")
        self.assertRedirects(response, "/accounts/login/?next=/espace-aidant/")

    def test_espace_aidant_home_url_triggers_the_right_view(self):
        found = resolve("/espace-aidant/")
        self.assertEqual(found.func, espace_aidant.home)

    def test_espace_aidant_home_url_triggers_the_right_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/espace-aidant/")
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")


@tag("usagers")
class UsagersIndexPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = AidantFactory()

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
        self.aidant = AidantFactory()
        self.usager = UsagerFactory()
        self.mandat = MandatFactory(
            organisation=self.aidant.organisation, usager=self.usager
        )
        AutorisationFactory(mandat=self.mandat)

    def test_usager_details_url_triggers_the_usager_details_view(self):
        found = resolve(f"/usagers/{self.usager.id}/")
        self.assertEqual(found.func, usagers.usager_details)

    def test_usager_details_url_triggers_the_usager_details_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        self.assertTemplateUsed(response, "aidants_connect_web/usager_details.html")

    def test_usager_details_template_dynamic_title(self):
        self.client.force_login(self.aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "<title>Aidants Connect - Homer Simpson</title>", response_content
        )
