from datetime import timedelta

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    OrganisationFactory,
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
class AutorisationCancelationConfirmPageTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.our_organisation = OrganisationFactory()
        self.our_aidant = AidantFactory(organisation=self.our_organisation)
        self.our_usager = UsagerFactory()

        mandat_valid = MandatFactory(
            organisation=self.our_organisation, usager=self.our_usager,
        )
        self.autorisation_valid = AutorisationFactory(
            mandat=mandat_valid, demarche="Revenus"
        )
        self.autorisation_revoked = AutorisationFactory(
            mandat=mandat_valid, demarche="Papiers", revocation_date=timezone.now()
        )

        mandat_expired = MandatFactory(
            organisation=self.our_organisation,
            usager=self.our_usager,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        self.autorisation_expired = AutorisationFactory(
            mandat=mandat_expired, demarche="Logement"
        )

        self.other_organisation = OrganisationFactory(name="Other Organisation")
        self.unrelated_usager = UsagerFactory()

        mandat_other_org_with_unrelated_usager = MandatFactory(
            organisation=self.other_organisation,
            usager=self.unrelated_usager,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        self.autorisation_other_orga_with_unrelated_usager = AutorisationFactory(
            mandat=mandat_other_org_with_unrelated_usager, demarche="Revenus"
        )

    def test_url_triggers_the_correct_view(self):
        found = resolve(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm"  # noqa
        )
        self.assertEqual(found.func, usagers.confirm_autorisation_cancelation)

        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm"
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/confirm_autorisation_cancelation.html",
        )
    def test_get_triggers_the_correct_template(self):
        self.client.force_login(self.our_aidant)

        response_incorrect_confirm_form = self.client.post(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm",
            data={},
        )
        self.assertTemplateUsed(
            response_incorrect_confirm_form,
            "aidants_connect_web/confirm_autorisation_cancelation.html",
        )

    def test_complete_post_triggers_redirect(self):
        self.client.force_login(self.our_aidant)

        response_correct_confirm_form = self.client.post(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_1_1.id}/cancel_confirm",
            data={"csrfmiddlewaretoken": "coucou"},
        )
        url = f"/usagers/{self.our_usager.id}/"
        self.assertRedirects(
            response_correct_confirm_form, url, fetch_redirect_response=False
        )

        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.autorisation_1_1.mandat.id}"
            f"/autorisations/{self.autorisation_3_1.id + 1}/cancel_confirm"
    def test_incomplete_post_triggers_error(self):
        self.client.force_login(self.our_aidant)
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
