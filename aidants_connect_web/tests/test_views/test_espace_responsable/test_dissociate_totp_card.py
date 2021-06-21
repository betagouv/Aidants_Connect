from django.test import tag, TestCase
from django.test.client import Client

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
)
from aidants_connect_web.models import CarteTOTP, Journal


@tag("responsable-structure")
class DissociateCarteTOTPTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create one responsable : Tom
        self.responsable_tom = AidantFactory(username="tom@tom.fr")
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)
        self.org_id = self.responsable_tom.organisation.id
        # Create one aidant : Tim
        self.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=self.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        self.dissociation_url = (
            f"/espace-responsable/organisation/{self.org_id}/"
            f"aidant/{self.aidant_tim.id}/"
        )

    def createCarteForTim(self):
        self.carte = CarteTOTPFactory(
            serial_number="A123", seed="FA169F10A9", aidant=self.aidant_tim
        )

    def createDeviceForTim(self, confirmed=True):
        self.device = TOTPDevice(
            tolerance=30,
            key=self.carte.seed,
            user=self.aidant_tim,
            step=60,
            confirmed=confirmed,
        )
        self.device.save()

    def doTheChecks(self):
        # Submit post and check redirection is correct
        self.client.force_login(self.responsable_tom)
        response = self.client.post(
            self.dissociation_url,
            data={"reason": "perte"},
        )
        self.assertRedirects(
            response, self.dissociation_url, fetch_redirect_response=False
        )
        # Check card still exists but that TOTP Device doesn't
        carte = CarteTOTP.objects.last()
        self.assertEqual(carte.serial_number, self.carte.serial_number)
        self.assertIsNone(carte.aidant)
        self.assertEqual(TOTPDevice.objects.count(), 0)
        # Check journal entry creation
        journal_entry = Journal.objects.last()
        self.assertEqual(
            journal_entry.action,
            "card_dissociation",
            "A Journal entry should have been created on card validation.",
        )

    def test_dissociation_in_nominal_case(self):
        self.createCarteForTim()
        self.createDeviceForTim()
        self.doTheChecks()

    def test_dissociation_without_existing_totp_device(self):
        self.createCarteForTim()
        self.doTheChecks()

    def test_dissociation_with_unconfirmed_totp_device(self):
        self.createCarteForTim()
        self.createDeviceForTim(confirmed=False)
        self.doTheChecks()
