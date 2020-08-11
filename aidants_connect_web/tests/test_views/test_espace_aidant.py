from datetime import timedelta

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.views import espace_aidant, usagers


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


@tag("usagers")
class AutorisationCancelConfirmPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_1 = AidantFactory()
        self.aidant_2 = AidantFactory(
            username="jacques@domain.user", email="jacques@domain.user"
        )
        self.usager_1 = UsagerFactory()
        self.usager_2 = UsagerFactory()

        mandat_1 = MandatFactory(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        self.autorisation_1_1 = AutorisationFactory(mandat=mandat_1, demarche="Revenus")
        self.autorisation_1_2 = AutorisationFactory(
            mandat=mandat_1, demarche="Papiers", revocation_date=timezone.now()
        )

        mandat_2 = MandatFactory(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        self.autorisation_2_1 = AutorisationFactory(
            mandat=mandat_2, demarche="Logement"
        )

        mandat_3 = MandatFactory(
            organisation=self.aidant_2.organisation,
            usager=self.usager_2,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        self.autorisation_3_1 = AutorisationFactory(mandat=mandat_3, demarche="Revenus")

    def test_usagers_autorisations_cancel_url_triggers_the_correct_view(self):
        found = resolve(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm"  # noqa
        )
        self.assertEqual(
            found.func, usagers.usagers_mandats_autorisations_cancel_confirm
        )

    def test_usagers_autorisations_cancel_url_triggers_the_correct_template(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm"
        )
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/usagers_mandats_autorisations_cancel_confirm.html",
        )

        response_incorrect_confirm_form = self.client.post(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm",
            data={},
        )
        self.assertTemplateUsed(
            response_incorrect_confirm_form,
            "aidants_connect_web/usagers_mandats_autorisations_cancel_confirm.html",
        )

        response_correct_confirm_form = self.client.post(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm",
            data={"csrfmiddlewaretoken": "coucou"},
        )
        url = f"/usagers/{self.usager_1.id}/"
        self.assertRedirects(
            response_correct_confirm_form, url, fetch_redirect_response=False
        )

    def test_non_existing_autorisation_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_3_1.id + 1}/cancel_confirm"
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_expired_autorisation_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_2_1.mandat.id}"
            f"/autorisations/{self.autorisation_2_1.id}/cancel_confirm"
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_revoked_autorisation_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_2.id}/cancel_confirm"
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_non_existing_usager_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_2.id + 1}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm"
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_wrong_usager_autorisation_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_3_1.mandat.id}"
            f"/autorisations/{self.autorisation_3_1.id}/cancel_confirm"
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_wrong_aidant_autorisation_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_2.id}/mandats/{self.autorisation_3_1.mandat.id}"
            f"/autorisations/{self.autorisation_3_1.id}/cancel_confirm"
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)
