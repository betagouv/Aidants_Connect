from unittest import mock
from unittest.mock import Mock

from django.contrib import messages as django_messages
from django.test import TestCase, override_settings, tag
from django.urls import resolve, reverse

from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.constants import OTP_APP_DEVICE_NAME
from aidants_connect_web.models import Aidant, Journal
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
@override_settings(FF_OTP_APP=True)
class AddAppOTPToAidantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.responsable_tom: Aidant = AidantFactory(
            username="tom@tom.fr", ff_otp_app=True
        )
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        cls.aidant_sarah: Aidant = AidantFactory(
            username="sarah@sarah.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Sarah",
            last_name="Onier",
        )

        TOTPDevice.objects.create(
            user=cls.aidant_sarah,
            name=OTP_APP_DEVICE_NAME % cls.aidant_sarah.pk,
        )

        cls.other_organisation = OrganisationFactory()
        cls.aidant_ahmed: Aidant = AidantFactory(
            username="ahmed@ahmed.fr",
            organisation=cls.other_organisation,
            first_name="Ahmed",
            last_name="Onier",
        )

    def test_triggers_the_right_view(self):
        found = resolve(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            )
        )
        self.assertEqual(found.func.view_class, espace_responsable.AddAppOTPToAidant)

    def test_renders_correct_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            )
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/app_otp_confirm.html"
        )

    def test_cant_add_otp_device_to_foreign_aidant(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.post(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_ahmed.pk},
            )
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual(0, self.aidant_ahmed.totpdevice_set.count())

    def test_cant_add_otp_device_twice(self):
        self.assertEqual(1, self.aidant_sarah.totpdevice_set.count())

        self.client.force_login(self.responsable_tom)

        response = self.client.post(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_sarah.pk},
            ),
            data={"otp_token": ""},  # Token shouldn't be verified
        )

        self.assertRedirects(
            response, reverse("espace_responsable_home"), fetch_redirect_response=False
        )
        self.assertEqual(
            "Il existe déjà une carte OTP numérique liée à ce profil. Si vous "
            "voulez en attacher une nouvelle, veuillez supprimer l’anciennne.",
            list(django_messages.get_messages(response.wsgi_request))[0].message,
        )
        self.assertEqual(1, self.aidant_sarah.totpdevice_set.count())

    @mock.patch.object(TOTP, "verify")
    def test_can_add_otp_device(self, mock_verify: Mock):
        self.assertEqual(0, self.aidant_tim.totpdevice_set.count())

        self.client.force_login(self.responsable_tom)

        self.client.get(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            )
        )

        # Won't create a record if the challenge is not passed
        mock_verify.return_value = False
        response = self.client.post(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            ),
            data={"otp_token": "654321"},
        )

        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/app_otp_confirm.html"
        )
        self.assertEqual(0, self.aidant_tim.totpdevice_set.count())

        # Creates the record if the challenge is passed
        mock_verify.return_value = True
        response = self.client.post(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            ),
            data={"otp_token": "123456"},
        )

        self.assertRedirects(
            response,
            reverse("espace_responsable_home"),
            fetch_redirect_response=False,
        )
        self.assertEqual(1, self.aidant_tim.totpdevice_set.count())
        self.assertTrue(self.aidant_tim.totpdevice_set.first().confirmed)


@tag("responsable-structure")
@override_settings(FF_OTP_APP=True)
class RemoveAppOTPToAidantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.responsable_tom: Aidant = AidantFactory(
            username="tom@tom.fr", ff_otp_app=True
        )
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.aidant_tim = AidantFactory(
            username="tim@tim.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        cls.aidant_sarah: Aidant = AidantFactory(
            username="sarah@sarah.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Sarah",
            last_name="Onier",
        )

        # Creating several to test all are being correctly deleted
        for _ in range(2):
            TOTPDevice.objects.create(
                user=cls.aidant_sarah,
                name=OTP_APP_DEVICE_NAME % cls.aidant_sarah.pk,
            )

        cls.other_organisation = OrganisationFactory()
        cls.aidant_ahmed: Aidant = AidantFactory(
            username="ahmed@ahmed.fr",
            organisation=cls.other_organisation,
            first_name="Ahmed",
            last_name="Onier",
        )

        TOTPDevice.objects.create(
            user=cls.aidant_ahmed,
            name=OTP_APP_DEVICE_NAME % cls.aidant_ahmed.pk,
        )

        cls.deactivated_aidant: Aidant = AidantFactory(
            username="deactivated@deactivated.fr",
            organisation=cls.responsable_tom.organisation,
            first_name="Deactivated",
            last_name="Onier",
            is_active=False,
        )

    def test_triggers_the_right_view(self):
        found = resolve(
            reverse(
                "espace_responsable_aidant_remove_app_otp",
                kwargs={"aidant_id": self.aidant_sarah.pk},
            )
        )
        self.assertEqual(
            found.func.view_class, espace_responsable.RemoveAppOTPFromAidant
        )

    def test_renders_correct_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            reverse(
                "espace_responsable_aidant_remove_app_otp",
                kwargs={"aidant_id": self.aidant_sarah.pk},
            )
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/app_otp_remove.html"
        )

    @mock.patch("aidants_connect_web.signals.card_associated_to_aidant.send")
    @mock.patch(
        "aidants_connect_web.views.espace_responsable.AddAppOTPToAidantForm.is_valid",
        return_value=True,
    )
    def test_add_otp_app(self, form_is_valid_mock, signal_send_mock: Mock):
        self.client.force_login(self.responsable_tom)

        self.assertEqual(0, self.aidant_tim.totpdevice_set.count())

        self.client.get(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            )
        )

        self.client.post(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            )
        )

        self.assertEqual(1, self.aidant_tim.totpdevice_set.count())

        journal_entry = Journal.objects.last()
        self.assertEqual(
            journal_entry.action,
            "card_association",
            "A Journal entry should have been created on card association.",
        )

        signal_send_mock.assert_called_with(
            None, otp_device=self.aidant_tim.totpdevice_set.first()
        )

    def test_cant_remove_otp_device_to_foreign_aidant(self):
        self.client.force_login(self.responsable_tom)

        self.assertEqual(1, self.aidant_ahmed.totpdevice_set.count())

        response = self.client.post(
            reverse(
                "espace_responsable_aidant_remove_app_otp",
                kwargs={"aidant_id": self.aidant_ahmed.pk},
            )
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual(1, self.aidant_ahmed.totpdevice_set.count())

    def test_remove_otp_app_from_aidant_without_top_app(self):
        self.client.force_login(self.responsable_tom)

        self.assertEqual(0, self.aidant_tim.totpdevice_set.count())

        response = self.client.post(
            reverse(
                "espace_responsable_aidant_remove_app_otp",
                kwargs={"aidant_id": self.aidant_tim.pk},
            )
        )

        self.assertRedirects(
            response, reverse("espace_responsable_home"), fetch_redirect_response=False
        )
        self.assertEqual(0, self.aidant_tim.totpdevice_set.count())

    def test_remove_otp_app_from_aidant_with_top_app(self):
        self.client.force_login(self.responsable_tom)

        self.assertEqual(2, self.aidant_sarah.totpdevice_set.count())

        response = self.client.post(
            reverse(
                "espace_responsable_aidant_remove_app_otp",
                kwargs={"aidant_id": self.aidant_sarah.pk},
            )
        )

        self.assertRedirects(
            response, reverse("espace_responsable_home"), fetch_redirect_response=False
        )
        self.assertEqual(0, self.aidant_sarah.totpdevice_set.count())

    def test_redirect_cant_add_app_otp_if_user_is_deactivated(self):
        self.client.force_login(self.responsable_tom)

        self.assertFalse(self.deactivated_aidant.has_otp_app)

        response = self.client.post(
            reverse(
                "espace_responsable_aidant_add_app_otp",
                kwargs={"aidant_id": self.deactivated_aidant.pk},
            ),
        )
        self.assertRedirects(
            response,
            reverse("espace_responsable_home"),
            fetch_redirect_response=False,
        )
        self.deactivated_aidant.refresh_from_db()
        self.assertFalse(self.deactivated_aidant.has_otp_app)

        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            f"Le profil de {self.deactivated_aidant.get_full_name()} désactivé. "
            "Il est impossible de lui lier attacher une nouvelle carte OTP "
            "numérique.",
            messages[0].message,
        )
