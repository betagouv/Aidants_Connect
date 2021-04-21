from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from aidants_connect_web.tests.factories import (
    AidantFactory,
    OrganisationFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class EspaceResponsableHomePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.responsable_tom = AidantFactory(username="georges@plop.net")
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)
        self.aidant_john = AidantFactory(username="john@doe.du")

    def test_anonymous_user_cannot_access_espace_aidant_view(self):
        response = self.client.get("/espace-responsable/")
        self.assertRedirects(response, "/accounts/login/?next=/espace-responsable/")

    def test_navigation_menu_contains_a_link_for_the_responsable_structure(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get("/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Mon espace Responsable",
            response_content,
            (
                "Link to espace responsable is invisible to a responsable, "
                "it should be visible"
            ),
        )

    def test_navigation_menu_does_not_contain_a_link_for_the_aidant(self):
        self.client.force_login(self.aidant_john)
        response = self.client.get("/")
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "Mon espace Responsable",
            response_content,
            "Link to espace responsable is visible to an aidant, it should not",
        )

    def test_espace_responsable_home_url_triggers_the_right_view(self):
        found = resolve("/espace-responsable/")
        self.assertEqual(found.func, espace_responsable.home)

    def test_espace_responsable_home_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get("/espace-responsable/")
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/home.html"
        )


@tag("responsable-structure")
class EspaceResponsableOrganisationPage(TestCase):
    def setUp(self):
        self.client = Client()
        self.responsable_tom = AidantFactory(username="georges@plop.net")
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)
        self.id_organisation = self.responsable_tom.organisation.id
        self.autre_organisation = OrganisationFactory()

    def test_anonymous_user_cannot_access_espace_responsable_view(self):
        response = self.client.get("/espace-responsable/")
        self.assertRedirects(response, "/accounts/login/?next=/espace-responsable/")

    def test_espace_responsable_organisation_url_triggers_the_right_view(self):
        self.client.force_login(self.responsable_tom)
        found = resolve(f"/espace-responsable/organisation/{self.id_organisation}")
        self.assertEqual(found.func, espace_responsable.organisation)

    def test_espace_responsable_organisation_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            f"/espace-responsable/organisation/{self.id_organisation}"
        )
        self.assertEqual(
            response.status_code,
            200,
            "trying to get "
            f"/espace-responsable/organisation/{self.id_organisation}/",
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/organisation.html"
        )

    def test_responsable_cannot_see_an_organisation_they_are_not_responsible_for(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            f"/espace-responsable/organisation/{self.autre_organisation.id}"
        )
        self.assertEqual(response.status_code, 404)
