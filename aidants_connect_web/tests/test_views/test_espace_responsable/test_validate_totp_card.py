from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class ValidateCarteTOTPTests(TestCase):
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
        self.carte = CarteTOTPFactory(
            serial_number="A123", seed="zzzz", aidant=self.aidant_tim
        )
        self.org_id = self.responsable_tom.organisation.id
        # Create one TOTP Device
        self.device = TOTPDevice(
            tolerance=15, key=self.carte.seed, user=self.aidant_tim, step=60
        )
        self.association_url = (
            f"/espace-responsable/organisation/{self.org_id}/"
            f"aidant/{self.aidant_tim.id}/associer-carte-totp"
        )
        self.validation_url = (
            f"/espace-responsable/organisation/{self.org_id}/"
            f"aidant/{self.aidant_tim.id}/valider-carte-totp"
        )

    def test_validation_page_triggers_the_right_view(self):
        found = resolve(self.validation_url)
        self.assertEqual(found.func, espace_responsable.validate_aidant_carte_totp)

    def test_validation_page_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.validation_url)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/validate-carte-totp.html"
        )
