from django.core import mail
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


@tag("responsable-structure")
class EspaceResponsableRemoveAidantOrganisationsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        organisation = OrganisationFactory(name="Beta Gouv")
        responsable = AidantFactory(organisation=organisation)
        responsable.responsable_de.add(responsable.organisation)
        responsable.responsable_de.add(OrganisationFactory())
        cls.responsable_of_2 = responsable

        aidant = AidantFactory(organisation=responsable.organisation)
        aidant.organisations.set(responsable.responsable_de.all())
        aidant.organisations.add(OrganisationFactory())
        cls.aidant = aidant

        aidant_referent = AidantFactory(organisation=responsable.organisation)
        aidant_referent.organisations.set(responsable.responsable_de.all())
        aidant_referent.responsable_de.set(responsable.responsable_de.all())
        aidant_referent.organisations.add(OrganisationFactory())
        cls.aidant_referent = aidant_referent

    def get_form_url(self, aidant, organisation):
        return (
            f"/espace-responsable/aidant/{aidant.id}/"
            f"supprimer-organisation/{organisation.id}/"
        )

    def test_remove_from_organisation(self):
        responsable = self.responsable_of_2
        aidant = self.aidant
        self.client.force_login(responsable)

        self.assertEqual(len(aidant.organisations.all()), 3)
        response = self.client.post(
            self.get_form_url(aidant, responsable.organisation),
        )
        self.assertRedirects(response, reverse("espace_responsable_aidants"))
        aidant.refresh_from_db()
        self.assertEqual(len(aidant.organisations.all()), 2)

        self.assertEqual(len(mail.outbox), 1)
        mail_content = mail.outbox[0].body
        mail_subject = mail.outbox[0].subject
        mail_recipient = mail.outbox[0].recipients()
        self.assertIn(aidant.email, mail_recipient)
        self.assertIn(
            "La liste des organisations dont vous faites partie a changé", mail_subject
        )
        self.assertIn(
            "Vous ne pouvez plus créer des mandats pour Beta Gouv", mail_content
        )

    def test_remove_referent_from_organisation(self):
        responsable = self.responsable_of_2
        aidant_referent = self.aidant_referent
        self.client.force_login(responsable)

        self.assertEqual(len(aidant_referent.organisations.all()), 3)
        self.assertEqual(len(aidant_referent.responsable_de.all()), 2)
        self.client.post(
            self.get_form_url(aidant_referent, responsable.organisation),
        )
        aidant_referent.refresh_from_db()
        self.assertEqual(len(aidant_referent.organisations.all()), 2)
        self.assertEqual(len(aidant_referent.responsable_de.all()), 1)
