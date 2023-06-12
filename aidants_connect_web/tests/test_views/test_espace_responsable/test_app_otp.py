from binascii import unhexlify

from django.contrib import messages as django_messages
from django.test import TestCase, tag
from django.urls import resolve, reverse
from django.utils import timezone

from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from freezegun import freeze_time

from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class AddAppOTPToAidantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.responsable_tom: Aidant = AidantFactory(username="tom@tom.fr")
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
            name=TOTPDevice.APP_DEVICE_NAME % cls.aidant_sarah.pk,
            tolerance=2,
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
                kwargs={"aidant_id": self.aidant_ahmed.pk},
            )
        )
        self.assertEqual(found.func.view_class, espace_responsable.AddAppOTPToAidant)

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
            [
                "Il existe déjà une application OTP liée à ce profil. Si vous "
                + "voulez en attacher une nouvelle, veuillez supprimer l'anciennne."
            ],
            [
                item.message
                for item in django_messages.get_messages(response.wsgi_request)
            ],
        )
        self.assertEqual(1, self.aidant_sarah.totpdevice_set.count())

    def test_can_add_unconfirmed_otp_device(self):
        now = timezone.now()
        with freeze_time(now):  # Freezing time to avoid submitting an expired token
            self.assertEqual(0, self.aidant_tim.totpdevice_set.count())

            self.client.force_login(self.responsable_tom)

            self.client.get(
                reverse(
                    "espace_responsable_aidant_add_app_otp",
                    kwargs={"aidant_id": self.aidant_tim.pk},
                )
            )

            otp_device = self.client.session["otp_device"]
            token = TOTP(
                key=unhexlify(otp_device["key"].encode()),
                step=otp_device["step"],
                t0=otp_device["t0"],
                digits=otp_device["digits"],
                drift=otp_device["drift"],
            ).token()

            response = self.client.post(
                reverse(
                    "espace_responsable_aidant_add_app_otp",
                    kwargs={"aidant_id": self.aidant_tim.pk},
                ),
                data={"otp_token": token},
            )

            self.assertRedirects(
                response,
                reverse("espace_responsable_home"),
                fetch_redirect_response=False,
            )
            self.assertEqual(1, self.aidant_tim.totpdevice_set.count())
            self.assertTrue(self.aidant_tim.totpdevice_set.first().confirmed)


@tag("responsable-structure")
class RemoveAppOTPToAidantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.responsable_tom: Aidant = AidantFactory(username="tom@tom.fr")
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
                name=TOTPDevice.APP_DEVICE_NAME % cls.aidant_sarah.pk,
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
            name=TOTPDevice.APP_DEVICE_NAME % cls.aidant_ahmed.pk,
        )

    def test_triggers_the_right_view(self):
        found = resolve(
            reverse(
                "espace_responsable_aidant_remove_app_otp",
                kwargs={"aidant_id": self.aidant_ahmed.pk},
            )
        )
        self.assertEqual(
            found.func.view_class, espace_responsable.RemoveAppOTPFromAidant
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
