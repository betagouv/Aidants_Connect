from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, tag
from django.test.client import Client
from django.urls import reverse

from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from import_export.results import Result

from aidants_connect.admin import VisibleToAdminMetier, VisibleToTechAdmin
from aidants_connect_web.admin import CarteTOTPAdmin
from aidants_connect_web.constants import HabilitationRequestStatuses
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    Connection,
    HabilitationRequest,
    Journal,
    Mandat,
    Organisation,
    Usager,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    HabilitationRequestFactory,
    TOTPDeviceFactory,
    UsagerFactory,
)


@tag("admin")
class LoginAttemptAdminPageTests(TestCase):
    def test_sidebar_is_not_in_login_admin_page(self):
        admin = settings.ADMIN_URL
        amac_client = Client()
        response = amac_client.get(f"/{admin}login", follow=True)
        self.assertTemplateUsed(response, "aidants_connect_web/admin/login.html")
        self.assertNotContains(response, "nav-sidebar")


@tag("admin")
class VisibleToTechAdminTests(TestCase):
    def test_visible_to_tech_admin_mixin_and_superuser(self):
        user = AidantFactory(is_staff=True, is_superuser=True)
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        tech_mixin = VisibleToTechAdmin()
        self.assertTrue(tech_mixin.has_module_permission(request))
        self.assertTrue(tech_mixin.has_view_permission(request))
        self.assertTrue(tech_mixin.has_add_permission(request))
        self.assertTrue(tech_mixin.has_change_permission(request))
        self.assertTrue(tech_mixin.has_delete_permission(request))

    def test_visible_to_tech_admin_mixin_and_is_staff_user(self):
        user = AidantFactory(is_staff=True, is_superuser=False)
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        tech_mixin = VisibleToTechAdmin()
        self.assertFalse(tech_mixin.has_module_permission(request))
        self.assertFalse(tech_mixin.has_view_permission(request))
        self.assertFalse(tech_mixin.has_add_permission(request))
        self.assertFalse(tech_mixin.has_change_permission(request))
        self.assertFalse(tech_mixin.has_delete_permission(request))

    def test_visible_to_tech_admin_mixin_and_anonymous_user(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        tech_mixin = VisibleToTechAdmin()
        self.assertFalse(tech_mixin.has_module_permission(request))
        self.assertFalse(tech_mixin.has_view_permission(request))
        self.assertFalse(tech_mixin.has_add_permission(request))
        self.assertFalse(tech_mixin.has_change_permission(request))
        self.assertFalse(tech_mixin.has_delete_permission(request))


@tag("admin")
class VisibleToAdminMetierTests(TestCase):
    def test_visible_to_amac_superuser(self):
        user = AidantFactory(is_staff=True, is_superuser=True)
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        admin_mixin = VisibleToAdminMetier()
        self.assertTrue(admin_mixin.has_module_permission(request))
        self.assertTrue(admin_mixin.has_view_permission(request))
        self.assertTrue(admin_mixin.has_add_permission(request))
        self.assertTrue(admin_mixin.has_change_permission(request))
        self.assertTrue(admin_mixin.has_delete_permission(request))

    def test_visible_to_amac_is_staff(self):
        user = AidantFactory(is_staff=True, is_superuser=False)
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        admin_mixin = VisibleToAdminMetier()
        self.assertTrue(admin_mixin.has_module_permission(request))
        self.assertTrue(admin_mixin.has_view_permission(request))
        self.assertTrue(admin_mixin.has_add_permission(request))
        self.assertTrue(admin_mixin.has_change_permission(request))
        self.assertTrue(admin_mixin.has_delete_permission(request))

    def test_visible_to_amac_anonymous(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        admin_mixin = VisibleToAdminMetier()
        self.assertFalse(admin_mixin.has_module_permission(request))
        self.assertFalse(admin_mixin.has_view_permission(request))
        self.assertFalse(admin_mixin.has_add_permission(request))
        self.assertFalse(admin_mixin.has_change_permission(request))
        self.assertFalse(admin_mixin.has_delete_permission(request))


@tag("admin")
class VisibilityAdminPageTests(TestCase):
    only_by_atac_models = [Mandat, Usager, Connection, Journal]
    amac_models = [
        Aidant,
        CarteTOTP,
        HabilitationRequest,
        StaticDevice,
        TOTPDevice,
        Organisation,
    ]

    @classmethod
    def setUpTestData(cls):
        cls.amac_user = AidantFactory(
            is_staff=True,
            is_superuser=False,
        )
        cls.amac_user.set_password("password")
        cls.amac_user.save()
        amac_device = StaticDevice.objects.create(user=cls.amac_user, name="Device")

        cls.amac_client = Client()
        cls.amac_client.force_login(cls.amac_user)
        # we need do this :
        # https://docs.djangoproject.com/en/3.1/topics/testing/tools/#django.test.Client.session
        amac_session = cls.amac_client.session
        amac_session[DEVICE_ID_SESSION_KEY] = amac_device.persistent_id
        amac_session.save()

        cls.atac_user = AidantFactory(
            is_staff=True,
            is_superuser=True,
        )
        cls.atac_user.set_password("password")
        cls.atac_user.save()
        atac_device = StaticDevice.objects.create(user=cls.atac_user, name="Device")

        cls.atac_client = Client()
        cls.atac_client.force_login(cls.atac_user)
        # we need do this :
        # https://docs.djangoproject.com/en/3.1/topics/testing/tools/#django.test.Client.session
        atac_session = cls.atac_client.session
        atac_session[DEVICE_ID_SESSION_KEY] = atac_device.persistent_id
        atac_session.save()

    def test_views_visible_only_by_atac_dont_visible_by_amac_users(self):
        for model in self.only_by_atac_models:
            url_root = f"admin:{model._meta.app_label}_{model.__name__.lower()}"
            list_url = reverse(url_root + "_changelist")
            response = self.amac_client.get(list_url)
            self.assertEqual(response.status_code, 403)

    def test_views_visible_only_by_atac_were_visible_by_atac_users(self):
        for model in self.only_by_atac_models:
            url_root = f"admin:{model._meta.app_label}_{model.__name__.lower()}"
            list_url = reverse(url_root + "_changelist")
            response = self.atac_client.get(list_url)
            self.assertEqual(response.status_code, 200)

    def test_views_visible_by_amac_were_visible_by_amac_users(self):
        for model in self.amac_models:
            url_root = f"admin:{model._meta.app_label}_{model.__name__.lower()}"
            list_url = reverse(url_root + "_changelist")
            response = self.amac_client.get(list_url)
            self.assertEqual(response.status_code, 200)

    def test_views_visible_by_amac_were_visible_by_atac_users(self):
        for model in self.amac_models:
            url_root = f"admin:{model._meta.app_label}_{model.__name__.lower()}"
            list_url = reverse(url_root + "_changelist")
            response = self.atac_client.get(list_url)
            self.assertEqual(response.status_code, 200)


@tag("admin")
class JournalAdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.atac_user = AidantFactory(
            is_staff=True,
            is_superuser=True,
        )
        cls.atac_user.set_password("password")
        cls.atac_user.save()
        cls.atac_device = StaticDevice.objects.create(user=cls.atac_user, name="Device")

        cls.atac_client = Client()
        cls.atac_client.force_login(cls.atac_user)
        atac_session = cls.atac_client.session
        atac_session[DEVICE_ID_SESSION_KEY] = cls.atac_device.persistent_id
        atac_session.save()
        url_root = f"admin:{Journal._meta.app_label}_{Journal.__name__.lower()}"
        cls.url_root = url_root

    def test_cant_delete_journal_by_admin_views(cls):
        cls.assertEqual(Journal.objects.count(), 1)
        journal = Journal.objects.all()[0]
        url = reverse(cls.url_root + "_delete", args=(journal.pk,))
        response = cls.atac_client.get(url)
        cls.assertEqual(response.status_code, 403)

    def test_cant_add_journal_by_admin_views(cls):
        url = reverse(cls.url_root + "_add")
        response = cls.atac_client.get(url)
        cls.assertEqual(response.status_code, 403)


@tag("admin")
class UsagerAdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.atac_user = AidantFactory(
            is_staff=True,
            is_superuser=True,
        )
        cls.atac_user.set_password("password")
        cls.atac_user.save()
        cls.atac_device = StaticDevice.objects.create(user=cls.atac_user, name="Device")

        cls.usager = UsagerFactory()

        cls.atac_client = Client()
        cls.atac_client.force_login(cls.atac_user)
        atac_session = cls.atac_client.session
        atac_session[DEVICE_ID_SESSION_KEY] = cls.atac_device.persistent_id
        atac_session.save()
        url_root = f"admin:{Journal._meta.app_label}_{Usager.__name__.lower()}"
        cls.url_root = url_root

    def test_can_change_usager_by_admin_views(self):
        url = reverse(self.url_root + "_change", args=(self.usager.pk,))
        response = self.atac_client.get(url)
        self.assertEqual(response.status_code, 200)


@tag("admin")
class TOTPCardAdminPageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = OTPAdminSite(OTPAdminSite.name)
        cls.tested = CarteTOTPAdmin(CarteTOTP, cls.admin)

    @classmethod
    def setUpTestData(cls):
        cls.bizdev_user = AidantFactory(
            is_staff=True,
            is_superuser=False,
        )
        cls.bizdev_user.set_password("password")
        cls.bizdev_user.save()
        cls.bizdev_device = StaticDevice.objects.create(
            user=cls.bizdev_user, name="Device"
        )

        cls.usager = UsagerFactory()

        cls.bizdev_client = Client()
        cls.bizdev_client.force_login(cls.bizdev_user)
        bizdev_session = cls.bizdev_client.session
        bizdev_session[DEVICE_ID_SESSION_KEY] = cls.bizdev_device.persistent_id
        bizdev_session.save()

    def test_associate_button_is_displayed(self):
        card = CarteTOTPFactory()
        card_change_url = reverse(
            "otpadmin:aidants_connect_web_cartetotp_change",
            args=(card.id,),
        )
        response = self.bizdev_client.get(card_change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lier la carte à un aidant")

    def test_dissociate_button_is_displayed(self):
        card = CarteTOTPFactory(aidant=AidantFactory())
        card_change_url = reverse(
            "otpadmin:aidants_connect_web_cartetotp_change",
            args=(card.id,),
        )
        response = self.bizdev_client.get(card_change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dissocier la carte de l’aidant")
        self.assertContains(response, "Créer un TOTP Device manquant")

    def test_diagnostic_totp(self):
        tested = self.tested

        # Cases in which everything is fine
        # Not linked to any aidant or totp device
        card_ok1 = CarteTOTPFactory()
        # Linked to exactly one device and one aidant
        card_ok2 = CarteTOTPFactory(aidant=AidantFactory())
        TOTPDeviceFactory(key=card_ok2.seed, user=card_ok2.aidant)
        self.assertIn("Tout va bien", tested.totp_devices_diagnostic(card_ok1))
        self.assertIn("Tout va bien", tested.totp_devices_diagnostic(card_ok2))

        # Not linked to an aidant, but has a totp device
        card_ko1 = CarteTOTPFactory()
        TOTPDeviceFactory(key=card_ko1.seed, user=AidantFactory())
        self.assertIn(
            "Cette carte devrait être associée à l’aidant",
            tested.totp_devices_diagnostic(card_ko1),
        )

        # Card is linked to aidant but no device exists
        card_ko2 = CarteTOTPFactory(aidant=AidantFactory())
        self.assertIn(
            "Aucun device ne correspond à cette carte",
            tested.totp_devices_diagnostic(card_ko2),
        )

        # Card and device linked to different aidants
        card_ko3 = CarteTOTPFactory(aidant=AidantFactory())
        device_ko3 = TOTPDeviceFactory(key=card_ko3.seed, user=AidantFactory())
        self.assertIn(
            f"mais le device est assigné à {device_ko3.user}.",
            tested.totp_devices_diagnostic(card_ko3),
        )

        # Several devices exist
        card_ko4 = CarteTOTPFactory(aidant=AidantFactory())
        for _ in range(2):
            TOTPDeviceFactory(key=card_ko4.seed, user=card_ko4.aidant)

        self.assertIn(
            "Il faudrait garder un seul TOTP Device",
            tested.totp_devices_diagnostic(card_ko4),
        )

    def test_associate_aidant_get(self):
        card = CarteTOTPFactory()
        card_change_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_associate",
            args=(card.id,),
        )
        response = self.bizdev_client.get(card_change_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/admin/carte_totp/associate.html"
        )
        self.assertContains(response, "Saisissez l'aidant ci-dessous.")

    def test_dissociate_aidant_get(self):
        aidant = AidantFactory(last_name="Delacour", first_name="Joël")
        card = CarteTOTPFactory(aidant=aidant)
        card_change_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_dissociate",
            args=(card.id,),
        )
        response = self.bizdev_client.get(card_change_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/admin/carte_totp/dissociate.html"
        )
        self.assertContains(response, f"Séparer la carte {card} de {aidant}")

    def test_associate_aidant_post(self):
        card = CarteTOTPFactory()
        card_associate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_associate",
            args=(card.id,),
        )
        aidant = AidantFactory()
        self.bizdev_client.post(card_associate_url, {"aidant": aidant.id})

        card_db = CarteTOTP.objects.get(id=card.id)
        totp_device = TOTPDevice.objects.get(user=aidant)
        self.assertEqual(card_db.aidant, aidant)
        self.assertEqual(card_db.seed, totp_device.key)
        self.assertTrue(totp_device.confirmed)

    def test_associate_aidant_whith_already_another_card(self):
        aidant = AidantFactory()
        CarteTOTPFactory(aidant=aidant)
        card = CarteTOTPFactory()
        card_associate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_associate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_associate_url, {"aidant": aidant.id})
        self.assertRedirects(
            response, card_associate_url, fetch_redirect_response=False
        )
        response = self.bizdev_client.get(card_associate_url)
        self.assertContains(response, f"L’aidant {aidant} a déjà une carte TOTP.")
        card_db = CarteTOTP.objects.get(id=card.id)
        self.assertIsNone(card_db.aidant)

    def test_associate_aidant_whith_already_totp_device(self):
        aidant = AidantFactory()
        card = CarteTOTPFactory()
        TOTPDeviceFactory(key=card.seed, user=aidant)
        card_associate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_associate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_associate_url, {"aidant": aidant.id})
        self.assertNotEqual(response.status_code, 500)
        card_db = CarteTOTP.objects.get(id=card.id)
        self.assertEqual(card_db.aidant, aidant)

    def test_reassociate_aidant_whithout_totp_device(self):
        aidant = AidantFactory()
        card = CarteTOTPFactory(aidant=aidant)
        card_associate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_associate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_associate_url, {"aidant": aidant.id})
        self.assertNotEqual(response.status_code, 500)
        card_db = CarteTOTP.objects.get(id=card.id)
        self.assertEqual(card_db.aidant, aidant)
        totp_device = TOTPDevice.objects.get(user=aidant)
        self.assertEqual(totp_device.key, card.seed)

    def test_dissociate_aidant_whith_totp_device(self):
        aidant = AidantFactory()
        totp_device = TOTPDeviceFactory(user=aidant)
        card = CarteTOTPFactory(aidant=aidant, seed=totp_device.key)
        card_dissociate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_dissociate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_dissociate_url)
        self.assertNotEqual(response.status_code, 500)
        card_db = CarteTOTP.objects.get(id=card.id)
        self.assertIsNone(card_db.aidant)
        self.assertEqual(0, TOTPDevice.objects.filter(user=aidant).count())

    def test_do_not_destroy_unrelated_totp_device(self):
        aidant_tim = AidantFactory()
        aidant_tom = AidantFactory()
        totp_device = TOTPDeviceFactory(user=aidant_tim)
        card = CarteTOTPFactory(aidant=aidant_tom, seed=totp_device.key)
        card_dissociate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_dissociate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_dissociate_url)
        self.assertNotEqual(response.status_code, 500)
        card_db = CarteTOTP.objects.get(id=card.id)
        self.assertIsNone(card_db.aidant)
        # device should be deleted only if it is associated with the same aidant
        self.assertEqual(1, TOTPDevice.objects.filter(user=aidant_tim).count())

    def test_dissociate_aidant_whithout_totp_device(self):
        aidant = AidantFactory()
        card = CarteTOTPFactory(aidant=aidant)
        card_dissociate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_dissociate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_dissociate_url)
        self.assertNotEqual(response.status_code, 500)
        card_db = CarteTOTP.objects.get(id=card.id)
        self.assertIsNone(card_db.aidant)
        self.assertEqual(0, TOTPDevice.objects.filter(user=aidant).count())

    def test_dissociate_on_card_without_aidant(self):
        card = CarteTOTPFactory()
        card_dissociate_url = reverse(
            "otpadmin:aidants_connect_web_carte_totp_dissociate",
            args=(card.id,),
        )
        response = self.bizdev_client.post(card_dissociate_url)
        self.assertNotEqual(response.status_code, 500)


@tag("admin")
class TotpCardsImportTests(TestCase):
    def setUp(self):
        self.admin = OTPAdminSite(OTPAdminSite.name)

    def test_log_entry_is_added(self):
        initial_count = Journal.objects.count()

        user = AidantFactory(is_staff=True, is_superuser=True)
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user

        result = Result()

        a = CarteTOTPAdmin(CarteTOTP, self.admin)
        a.generate_log_entries(result, request)

        self.assertEqual(Journal.objects.count(), 1 + initial_count)


@tag("admin")
class HabilitationRequestAdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = OTPAdminSite(OTPAdminSite.name)
        cls.url = reverse(
            "otpadmin:aidants_connect_web_habilitation_request_mass_validate"
        )
        cls.list_url = reverse(
            "otpadmin:aidants_connect_web_habilitationrequest_changelist"
        )
        cls.bizdev_user = AidantFactory(
            is_staff=True,
            is_superuser=False,
        )
        cls.bizdev_user.set_password("password")
        cls.bizdev_user.save()
        cls.bizdev_device = StaticDevice.objects.create(
            user=cls.bizdev_user, name="Device"
        )

        cls.bizdev_client = Client()
        cls.bizdev_client.force_login(cls.bizdev_user)
        bizdev_session = cls.bizdev_client.session
        bizdev_session[DEVICE_ID_SESSION_KEY] = cls.bizdev_device.persistent_id
        bizdev_session.save()

    def test_mass_habilitation_page_is_available(self):
        response = self.bizdev_client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Habilitation en masse à partir des adresses e-mail"
        )

    def test_mass_habilitation_on_only_valid_addresses(self):
        for _ in range(2):
            HabilitationRequestFactory()
        emails = tuple(obj.email for obj in HabilitationRequest.objects.all())
        response = self.bizdev_client.post(self.url, {"email_list": "\n".join(emails)})
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        response = self.bizdev_client.get(self.list_url)
        self.assertContains(response, "Les 2 demandes ont bien été validées.")
        for email in emails:
            habilitation_request = HabilitationRequest.objects.get(email=email)
            self.assertEqual(
                habilitation_request.status,
                HabilitationRequestStatuses.STATUS_VALIDATED,
            )
            self.assertTrue(Aidant.objects.filter(email=email).exists())

    def test_mass_habilitation_on_canceled_status(self):
        for _ in range(2):
            HabilitationRequestFactory(
                status=HabilitationRequestStatuses.STATUS_CANCELLED
            )
        self.assertEqual(2, HabilitationRequest.objects.all().count())
        emails = tuple(obj.email for obj in HabilitationRequest.objects.all())
        response = self.bizdev_client.post(self.url, {"email_list": "\n".join(emails)})
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        response = self.bizdev_client.get(self.list_url)
        self.assertContains(response, "Les 2 demandes ont bien été validées.")
        for email in emails:
            habilitation_request = HabilitationRequest.objects.get(email=email)
            self.assertEqual(
                habilitation_request.status,
                HabilitationRequestStatuses.STATUS_VALIDATED,
            )
            self.assertTrue(Aidant.objects.filter(email=email).exists())

    def test_mass_habilitation_with_valid_and_invalid_addresses(self):
        for _ in range(5):
            HabilitationRequestFactory()
        valid_emails = (obj.email for obj in HabilitationRequest.objects.all())
        invalid_emails = ("jlfqksjqsdf@com.com", "qlfqf@non.net")
        emails = "\n".join(invalid_emails) + "\n" + "\n".join(valid_emails)
        response = self.bizdev_client.post(self.url, {"email_list": emails})
        self.assertEqual(response.status_code, 200)  # no redirection
        for email in valid_emails:
            habilitation_request = HabilitationRequest.objects.get(email=email)
            self.assertEqual(
                habilitation_request.status,
                HabilitationRequestStatuses.STATUS_VALIDATED,
            )
            self.assertTrue(Aidant.objects.filter(email=email).exists())
        self.assertContains(
            response,
            (
                "Les demandes suivantes ont été validées, les comptes aidant "
                "ont été créés"
            ),
        )
        self.assertContains(response, "2 adresses e-mails ont été ignorées.")
        self.assertContains(response, "Nous n'avons trouvé aucun")
