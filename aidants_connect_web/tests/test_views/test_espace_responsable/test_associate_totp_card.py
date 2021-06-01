from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
)
from aidants_connect_web.models import CarteTOTP
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class AssociateCarteTOTPTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create one responsable
        self.responsable_tom = AidantFactory(username="tom@tom.fr")
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)
        # Create one aidant
        self.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=self.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        # Create one carte TOTP
        self.carte = CarteTOTPFactory(serial_number="A123", seed="zzzz")
        self.org_id = self.responsable_tom.organisation.id
        self.association_url = (
            f"/espace-responsable/organisation/{self.org_id}/"
            f"aidant/{self.aidant_tim.id}/lier-carte"
        )
        self.validation_url = (
            f"/espace-responsable/organisation/{self.org_id}/"
            f"aidant/{self.aidant_tim.id}/valider-carte"
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

        # Check organisation page warns about activation
        response = self.client.get(f"/espace-responsable/organisation/{self.org_id}/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "Le fonctionnement de cette carte n'a pas été vérifié.",
            response_content,
            "Organization page should display a warning about activation.",
        )
