from datetime import timedelta

from django.contrib import messages as django_messages
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone

from aidants_connect_web.models import Connection, Journal, Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ExpiredOverYearMandatFactory,
    MandatFactory,
    OrganisationFactory,
    RevokedMandatFactory,
    UsagerFactory,
)


@tag("renew_mandat")
class RenewMandatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.organisation = OrganisationFactory()
        cls.aidant_thierry = AidantFactory(organisation=cls.organisation)
        device = cls.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="223456")

        cls.usager = UsagerFactory(given_name="Fabrice")

    def test_no_renew_button_displayed_if_expired_over_a_year(self):
        over_a_year_expired_mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() - timedelta(days=365),
            post__create_authorisations=["argent", "famille", "logement"],
        )
        self.assertFalse(
            over_a_year_expired_mandat.is_active,
            "Generated mandat should not be active",
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        response = self.client.get(reverse("usagers"))
        self.assertNotContains(response, "Renouveler")

    def test_no_renew_button_displayed_if_revoked_mandat(self):
        revoked_mandat = RevokedMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
            post__create_authorisations=["argent", "famille", "logement"],
        )
        self.assertTrue(
            revoked_mandat.was_explicitly_revoked,
            "Generated mandat should be explicitly revoked",
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        response = self.client.get(reverse("usagers"))
        self.assertNotContains(response, "Renouveler")

    def test_show_renew_button_if_any_renewable_mandats(self):
        less_than_a_year_expired_mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() - timedelta(days=5),
            post__create_authorisations=["argent", "famille", "logement"],
        )
        revoked_mandat = RevokedMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
            post__create_authorisations=["argent", "famille", "logement"],
        )
        over_a_year_expired_mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() - timedelta(days=365),
            post__create_authorisations=["argent", "famille", "logement"],
        )
        self.assertFalse(
            less_than_a_year_expired_mandat.is_active,
            "Generated mandat should not be active",
        )
        self.assertTrue(
            revoked_mandat.was_explicitly_revoked,
            "Generated mandat should be explicitly revoked",
        )
        self.assertFalse(
            over_a_year_expired_mandat.is_active,
            "Generated mandat should not be active",
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 3)
        response = self.client.get(reverse("usagers"))
        self.assertContains(response, "Renouveler")

    def test_renew_mandat_ok(self):
        MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        self.assertEqual(Connection.objects.count(), 0)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post(
            reverse("renew_mandat", args=(self.usager.pk,)), data=data
        )
        self.assertRedirects(response, reverse("new_mandat_recap"))
        self.assertEqual(Connection.objects.count(), 1)
        self.assertEqual(Mandat.objects.count(), 1)

    def test_renew_mandat_expired_ok(self):
        MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() - timedelta(days=5),
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        self.assertEqual(Connection.objects.count(), 0)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post(
            reverse("renew_mandat", args=(self.usager.pk,)), data=data
        )
        self.assertRedirects(response, reverse("new_mandat_recap"))
        self.assertEqual(Connection.objects.count(), 1)
        self.assertEqual(Mandat.objects.count(), 1)
        journals = Journal.objects.filter(action="init_renew_mandat")
        self.assertEqual(journals.count(), 1)
        self.assertEqual(journals[0].aidant, self.aidant_thierry)
        self.assertEqual(journals[0].usager, self.usager)

    def test_renew_mandat_expired_more_than_one_year_nok(self):
        ExpiredOverYearMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        self.assertEqual(Connection.objects.count(), 0)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post(
            reverse("renew_mandat", args=(self.usager.pk,)), data=data
        )
        self.assertRedirects(response, reverse("espace_aidant_home"))
        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            messages[0].message, "Cet usager n'a aucun mandat renouvelable."
        )
        self.assertEqual(Connection.objects.count(), 0)
        self.assertEqual(Mandat.objects.count(), 1)
        journals = Journal.objects.filter(action="init_renew_mandat")
        self.assertEqual(journals.count(), 0)

    def test_renew_revoked_mandat_nok(self):
        RevokedMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            post__create_authorisations=["famille", "social", "justice", "etranger"],
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        self.assertEqual(Connection.objects.count(), 0)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post(
            reverse("renew_mandat", args=(self.usager.pk,)), data=data
        )
        self.assertRedirects(response, reverse("espace_aidant_home"))
        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            messages[0].message, "Cet usager n'a aucun mandat renouvelable."
        )
        self.assertEqual(Connection.objects.count(), 0)
        self.assertEqual(Mandat.objects.count(), 1)
        journals = Journal.objects.filter(action="init_renew_mandat")
        self.assertEqual(journals.count(), 0)

    def test_renew_multiple_invalid_one_expired_ok(self):
        MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() - timedelta(days=5),
        )
        RevokedMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            post__create_authorisations=["famille", "social", "justice", "etranger"],
        )
        ExpiredOverYearMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 3)
        self.assertEqual(Connection.objects.count(), 0)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post(
            reverse("renew_mandat", args=(self.usager.pk,)), data=data
        )
        self.assertRedirects(response, reverse("new_mandat_recap"))
        self.assertEqual(Connection.objects.count(), 1)
        self.assertEqual(Mandat.objects.count(), 3)
        journals = Journal.objects.filter(action="init_renew_mandat")
        self.assertEqual(journals.count(), 1)
        self.assertEqual(journals[0].aidant, self.aidant_thierry)
        self.assertEqual(journals[0].usager, self.usager)
