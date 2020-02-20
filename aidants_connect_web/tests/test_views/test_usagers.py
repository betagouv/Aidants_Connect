from datetime import timedelta

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from aidants_connect_web.models import Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.views import usagers


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
        self.mandat = MandatFactory(aidant=self.aidant, usager=self.usager)

    def test_usager_details_url_triggers_the_usager_details_view(self):
        found = resolve(f"/usagers/{self.usager.id}/")
        self.assertEqual(found.func, usagers.usager_details)

    def test_usager_details_url_triggers_the_usager_details_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        self.assertTemplateUsed(response, "aidants_connect_web/usager_details.html")


@tag("usagers")
class MandatCancelConfirmPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_1 = AidantFactory()
        self.aidant_2 = AidantFactory(
            username="jacques@domain.user", email="jacques@domain.user"
        )
        self.usager_1 = UsagerFactory()
        self.usager_2 = UsagerFactory(sub="1234")
        self.mandat_1 = Mandat.objects.create(
            aidant=self.aidant_1,
            usager=self.usager_1,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        self.mandat_2 = Mandat.objects.create(
            aidant=self.aidant_2,
            usager=self.usager_2,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )

    def test_usagers_mandats_cancel_url_triggers_the_correct_view(self):
        found = resolve(
            f"/usagers/{self.usager_1.id}/mandats/{self.mandat_1.id}/cancel_confirm"
        )
        self.assertEqual(found.func, usagers.usagers_mandats_cancel_confirm)

    def test_usagers_mandats_cancel_url_triggers_the_correct_template(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.mandat_1.id}/cancel_confirm"
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/usagers_mandats_cancel_confirm.html"
        )

    def test_non_existing_mandat_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/3/cancel_confirm"
        )
        url = "/dashboard/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_non_existing_usager_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_2.id + 1}/mandats/{self.mandat_1.id}/cancel_confirm"
        )
        url = "/dashboard/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_wrong_usager_mandat_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_1.id}/mandats/{self.mandat_2.id}/cancel_confirm"
        )
        url = "/dashboard/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_wrong_aidant_mandat_triggers_redirect(self):
        self.client.force_login(self.aidant_1)
        response = self.client.get(
            f"/usagers/{self.usager_2.id}/mandats/{self.mandat_2.id}/cancel_confirm"
        )
        url = "/dashboard/"
        self.assertRedirects(response, url, fetch_redirect_response=False)
