from datetime import timedelta

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone

from aidants_connect_web.models import Connection, Mandat, Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    OrganisationFactory,
    UsagerFactory,
)


@tag("renew_mandat")
class RenewMandatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organisation = OrganisationFactory()
        self.aidant_thierry = AidantFactory(organisation=self.organisation)
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="223456")

        self.usager = UsagerFactory(given_name="Fabrice")

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
