from datetime import timedelta

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone

from aidants_connect_web.models import Connection, Mandat, Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    RevokedMandatFactory,
    OrganisationFactory,
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

    def test_no_renew_button_displayed_if_should_not(self):
        mandat = RevokedMandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
            post__create_authorisations=["argent", "famille", "logement"],
        )
        self.assertTrue(
            mandat.was_explicitly_revoked,
            "Generated mandat should be explicitly revoked",
        )
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Mandat.objects.count(), 1)
        response = self.client.get(reverse("usagers"))
        self.assertNotContains(response, "Renouveler")

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
