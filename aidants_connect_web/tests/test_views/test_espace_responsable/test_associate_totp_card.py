from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.models import CarteTOTP, Journal
from aidants_connect_web.tests.factories import AidantFactory, CarteTOTPFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class AssociateCarteTOTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Create one responsable
        cls.responsable_tom = AidantFactory(username="tom@tom.fr")
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        # Create one aidant
        cls.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        # Create one carte TOTP
        cls.carte = CarteTOTPFactory(serial_number="A123", seed="zzzz")
        cls.org_id = cls.responsable_tom.organisation.id
        cls.association_url = (
            f"/espace-responsable/aidant/{cls.aidant_tim.id}/lier-carte"
        )
        cls.validation_url = (
            f"/espace-responsable/aidant/{cls.aidant_tim.id}/valider-carte"
        )

    def test_association_page_triggers_the_right_view(self):
        found = resolve(self.association_url)
        self.assertEqual(found.func, espace_responsable.associate_aidant_carte_totp)

    def test_association_page_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.association_url)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/write-carte-totp-sn.html"
        )

    def test_post_a_sn_creates_a_totp_device(self):
        self.client.force_login(self.responsable_tom)

        # Submit post and check redirection is correct
        response = self.client.post(
            self.association_url,
            data={"serial_number": self.carte.serial_number},
        )
        self.assertRedirects(
            response, self.validation_url, fetch_redirect_response=False
        )
        # Check a TOTP Device was created
        self.assertEqual(TOTPDevice.objects.count(), 1, "No TOTP Device was created")

        # Check TOTP device is correct
        totp_device = TOTPDevice.objects.first()
        self.assertEqual(totp_device.key, self.carte.seed)
        self.assertEqual(totp_device.user, self.aidant_tim)
        self.assertFalse(totp_device.confirmed)

        # Check CarteTOTP object has been updated too
        card = CarteTOTP.objects.first()
        self.assertEqual(card.aidant, self.aidant_tim)

        # Check journal entry creation
        journal_entry = Journal.objects.last()
        self.assertEqual(
            journal_entry.action,
            "card_association",
            "A Journal entry should have been created on card association.",
        )

        # Check organisation page warns about activation
        response = self.client.get(f"/espace-responsable/organisation/{self.org_id}/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Le fonctionnement de cette carte n’a pas été vérifié.",
            response_content,
            "Organization page should display a warning about activation.",
        )
