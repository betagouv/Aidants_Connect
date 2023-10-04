from django.contrib import messages as django_messages
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.models import Aidant, Journal
from aidants_connect_web.tests.factories import AidantFactory, CarteTOTPFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class AssociateCarteTOTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Create one référent
        cls.responsable_tom = AidantFactory(username="tom@tom.fr")
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        # Create one aidant
        cls.aidant_tim: Aidant = AidantFactory(
            username="tim@tim.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        # Aidant with valid TOTP card
        cls.aidant_sarah: Aidant = AidantFactory(
            username="sarah@sarah.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Sarah",
            last_name="Onier",
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=True,
        )
        # Aidant deactivated aidant
        cls.deactivated_aidant: Aidant = AidantFactory(
            username="deactivated@deactivated.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Deactivated",
            last_name="Onier",
            is_active=False,
        )
        # Create one carte TOTP
        cls.carte = CarteTOTPFactory(seed="zzzz")
        cls.org_id = cls.responsable_tom.organisation.id
        cls.association_url = reverse(
            "espace_responsable_associate_totp",
            kwargs={"aidant_id": cls.aidant_tim.pk},
        )
        cls.validation_url = reverse(
            "espace_responsable_validate_totp",
            kwargs={"aidant_id": cls.aidant_tim.pk},
        )

    def test_association_page_triggers_the_right_view(self):
        found = resolve(self.association_url)
        self.assertEqual(
            found.func.view_class, espace_responsable.AssociateAidantCarteTOTP
        )

    def test_association_page_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.association_url)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/write-carte-totp-sn.html"
        )

    def test_redirect_if_aidant_has_a_totp_card(self):
        self.client.force_login(self.responsable_tom)
        expected_card = self.aidant_sarah.carte_totp.pk
        response = self.client.post(
            reverse(
                "espace_responsable_associate_totp",
                kwargs={"aidant_id": self.aidant_sarah.pk},
            ),
            data={"serial_number": self.carte.serial_number},
        )
        self.assertRedirects(
            response,
            reverse(
                "espace_responsable_aidant", kwargs={"aidant_id": self.aidant_sarah.id}
            ),
        )
        self.aidant_sarah.refresh_from_db()
        self.assertEqual(
            expected_card,
            self.aidant_sarah.carte_totp.pk,
            "TOTP shoudln'd have been modified",
        )

    def test_redirect_if_aidant_is_deactivated(self):
        self.client.force_login(self.responsable_tom)

        self.assertFalse(self.deactivated_aidant.has_a_carte_totp)

        response = self.client.post(
            reverse(
                "espace_responsable_associate_totp",
                kwargs={"aidant_id": self.deactivated_aidant.pk},
            ),
            data={"serial_number": self.carte.serial_number},
        )
        self.assertRedirects(
            response,
            reverse(
                "espace_responsable_aidant",
                kwargs={"aidant_id": self.deactivated_aidant.id},
            ),
        )
        self.deactivated_aidant.refresh_from_db()
        self.assertFalse(self.deactivated_aidant.has_a_carte_totp)

        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            f"Le compte de {self.deactivated_aidant.get_full_name()} est désactivé. "
            f"Il est impossible de lui attacher une nouvelle carte Aidant Connect",
            messages[0].message,
        )

    def test_post_a_sn_creates_a_totp_device(self):
        self.client.force_login(self.responsable_tom)

        previous_count = TOTPDevice.objects.count()
        self.assertFalse(self.aidant_tim.has_a_carte_totp)

        # Submit post and check redirection is correct
        response = self.client.post(
            self.association_url,
            data={"serial_number": self.carte.serial_number},
        )
        self.assertRedirects(
            response, self.validation_url, fetch_redirect_response=False
        )
        # Check a TOTP Device was created
        self.assertEqual(
            previous_count + 1, TOTPDevice.objects.count(), "No TOTP Device was created"
        )

        # Check TOTP device is correct
        self.aidant_tim.refresh_from_db()
        card = self.aidant_tim.carte_totp
        self.assertEqual(card.totp_device.key, self.carte.seed)
        self.assertEqual(card.totp_device.user, self.aidant_tim)
        self.assertFalse(card.totp_device.confirmed)

        # Check CarteTOTP object has been updated too
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
