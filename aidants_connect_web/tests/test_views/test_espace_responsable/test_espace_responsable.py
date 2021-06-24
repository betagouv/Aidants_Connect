from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.tests.factories import (
    AidantFactory,
    OrganisationFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class EspaceResponsableHomePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Tom is responsable of 2 structures
        cls.responsable_tom = AidantFactory(username="tom@baie.fr")
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.responsable_tom.responsable_de.add(OrganisationFactory())
        cls.responsable_tom.can_create_mandats = False
        # Tim is responsable of only one structure
        cls.responsable_tim = AidantFactory(username="tim@oree.fr")
        cls.responsable_tim.responsable_de.add(cls.responsable_tim.organisation)
        # John is a simple aidant
        cls.aidant_john = AidantFactory(username="john@doe.du")

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

    def test_hide_espace_aidant_from_responsable_who_cannot_create_mandats(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get("/")
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "Mon espace Aidant",
            response_content,
            (
                "Link to espace aidant is visible to a responsable without "
                " mandats permission, it should be invisible"
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

    def test_responsable_is_redirected_if_has_only_one_structure(self):
        self.client.force_login(self.responsable_tim)
        response = self.client.get("/espace-responsable/")
        self.assertRedirects(
            response,
            f"/espace-responsable/organisation/{self.responsable_tim.organisation.id}/",
        )


@tag("responsable-structure")
class EspaceResponsableOrganisationPage(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.responsable_tom = AidantFactory(username="georges@plop.net")
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.id_organisation = cls.responsable_tom.organisation.id
        cls.autre_organisation = OrganisationFactory()

    def test_espace_responsable_organisation_url_triggers_the_right_view(self):
        self.client.force_login(self.responsable_tom)
        found = resolve(f"/espace-responsable/organisation/{self.id_organisation}/")
        self.assertEqual(found.func, espace_responsable.organisation)

    def test_espace_responsable_organisation_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            f"/espace-responsable/organisation/{self.id_organisation}/"
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
            f"/espace-responsable/organisation/{self.autre_organisation.id}/"
        )
        self.assertEqual(response.status_code, 404)


@tag("responsable-structure")
class EspaceResponsableAidantPage(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.responsable_tom = AidantFactory(username="tom@tom.fr")
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.aidant_tim = AidantFactory(
            username="tim@tim.fr", organisation=cls.responsable_tom.organisation
        )
        cls.id_organisation = cls.responsable_tom.organisation.id
        cls.aidant_tim_url = (
            f"/espace-responsable/organisation/{cls.id_organisation}"
            f"/aidant/{cls.aidant_tim.id}/"
        )
        cls.autre_organisation = OrganisationFactory()
        cls.autre_aidant = AidantFactory(username="random@random.net")

    def test_espace_responsable_aidant_url_triggers_the_right_view(self):
        self.client.force_login(self.responsable_tom)
        found = resolve(self.aidant_tim_url)
        self.assertEqual(found.func, espace_responsable.aidant)

    def test_espace_responsable_aidant_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.aidant_tim_url)
        self.assertEqual(
            response.status_code,
            200,
            f"trying to get {self.aidant_tim_url}",
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/aidant.html"
        )

    def test_responsable_cannot_see_an_aidant_they_are_not_responsible_for(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            f"/espace-responsable/organisation/{self.autre_organisation.id}"
            f"/aidant/{self.aidant_tim.id}/"
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            f"/espace-responsable/organisation/{self.id_organisation}"
            f"/aidant/{self.autre_aidant.id}/"
        )
        self.assertEqual(response.status_code, 404)


@tag("responsable-structure")
class InsistOnTOTPDeviceActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        orga = OrganisationFactory()
        # Mario is a responsable without TOTP Device activated
        # => He should see the messages
        cls.responsable_mario = AidantFactory(
            username="mario@brosse.fr", organisation=orga
        )
        cls.responsable_mario.responsable_de.add(cls.responsable_mario.organisation)
        cls.responsable_mario.responsable_de.add(OrganisationFactory())
        # Mickey is a responsable with a TOTP Device activated
        # => He should not see the messages
        cls.responsable_mickey = AidantFactory(
            username="mickey@mousse.fr", organisation=orga
        )
        cls.responsable_mickey.responsable_de.add(cls.responsable_mickey.organisation)
        cls.responsable_mickey.responsable_de.add(OrganisationFactory())
        device = TOTPDevice(user=cls.responsable_mickey)
        device.save()
        # Roger is a responsable with an *inactive* TOTP Device
        # (e.g. after an unfinished card activation)
        # => He should see the messages
        cls.responsable_hubert = AidantFactory(
            username="hubert@lingot.fr", organisation=orga
        )
        cls.responsable_hubert.responsable_de.add(cls.responsable_hubert.organisation)
        cls.responsable_hubert.responsable_de.add(OrganisationFactory())
        device = TOTPDevice(user=cls.responsable_hubert, confirmed=False)
        device.save()
        # Guy has no TOTP Device but is a simple Aidant
        # => He should not see the messages.
        cls.aidant_guy = AidantFactory(username="guy@mauve.fr")

        cls.urls_responsables = (
            "/espace-aidant/",
            "/espace-responsable/",
            f"/espace-responsable/organisation/{orga.id}/",
        )

    def test_display_messages_to_reponsable_if_no_totp_device_exists(self):
        self.client.force_login(self.responsable_mario)
        for page in self.urls_responsables:
            response = self.client.get(page)
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "activer votre carte Aidants Connect",
                response_content,
                f"TOTP message is hidden on '{page}', it should be visible",
            )

    def test_display_messages_to_reponsable_if_the_totp_device_is_unconfirmed(self):
        self.client.force_login(self.responsable_hubert)
        for page in self.urls_responsables:
            response = self.client.get(page)
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "activer votre carte Aidants Connect",
                response_content,
                f"TOTP message is hidden on '{page}', it should be visible",
            )

    def test_hide_messages_from_reponsable_if_any_totp_device_is_activated(self):
        self.client.force_login(self.responsable_mickey)
        for page in self.urls_responsables:
            response = self.client.get(page)
            response_content = response.content.decode("utf-8")
            self.assertNotIn(
                "activer votre carte Aidants Connect",
                response_content,
                f"TOTP message is shown on '{page}', it should be hidden",
            )

    def test_hide_messages_from_aidants_even_without_totp_device(self):
        self.client.force_login(self.aidant_guy)
        response = self.client.get("/espace-aidant/")
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "activer votre carte Aidants Connect",
            response_content,
            "TOTP message is shown on espace-aidant, it should be hidden",
        )
