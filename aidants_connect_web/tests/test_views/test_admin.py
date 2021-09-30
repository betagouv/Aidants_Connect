from admin_honeypot.models import LoginAttempt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, tag, TestCase
from django.test.client import Client
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from import_export.results import Result

from aidants_connect_web.admin import (
    VisibleToAdminMetier,
    VisibleToTechAdmin,
    CarteTOTPAdmin,
)

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
    TOTPDeviceFactory,
    UsagerFactory,
)


@tag("admin")
class LoginAttemptAdminPageTests(TestCase):
    def test_honeypot_login_attempt_fails_gracefuly(self):
        login_attempt_id = LoginAttempt.objects.create(username="test").pk
        path = reverse(
            "admin:admin_honeypot_loginattempt_change", args=(login_attempt_id,)
        )
        admin = settings.ADMIN_URL
        admin_url = f"/{admin}admin_honeypot/loginattempt/{login_attempt_id}/change/"
        self.assertEqual(admin_url, path)

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
    amac_models = [Organisation, Aidant, StaticDevice, TOTPDevice, HabilitationRequest]

    @classmethod
    def setUpTestData(cls):
        cls.amac_user = AidantFactory(
            username="amac@email.com",
            email="amac@email.com",
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
            username="atac@email.com",
            email="atac@email.com",
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
            username="atac@email.com",
            email="atac@email.com",
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
            username="atac@email.com",
            email="atac@email.com",
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
    def setUpTestData(cls):
        cls.admin = OTPAdminSite(OTPAdminSite.name)
        cls.tested = CarteTOTPAdmin(CarteTOTP, cls.admin)

        cls.bizdev_user = AidantFactory(
            username="bizdev@email.com",
            email="bizdev@email.com",
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
        card_ok2 = CarteTOTPFactory(aidant=AidantFactory(username="alicia"))
        TOTPDeviceFactory(key=card_ok2.seed, user=card_ok2.aidant)
        self.assertIn("Tout va bien", tested.totp_devices_diagnostic(card_ok1))
        self.assertIn("Tout va bien", tested.totp_devices_diagnostic(card_ok2))

        # Not linked to an aidant, but has a totp device
        card_ko1 = CarteTOTPFactory()
        TOTPDeviceFactory(key=card_ko1.seed, user=AidantFactory(username="bobdylane"))
        self.assertIn(
            "Cette carte devrait être associée à l’aidant",
            tested.totp_devices_diagnostic(card_ko1),
        )

        # Card is linked to aidant but no device exists
        card_ko2 = CarteTOTPFactory(aidant=AidantFactory(username="claudia"))
        self.assertIn(
            "Aucun device ne correspond à cette carte",
            tested.totp_devices_diagnostic(card_ko2),
        )

        # Card and device linked to different aidants
        card_ko3 = CarteTOTPFactory(aidant=AidantFactory(username="damian"))
        device_ko3 = TOTPDeviceFactory(
            key=card_ko3.seed, user=AidantFactory(username="eloise")
        )
        self.assertIn(
            f"mais le device est assigné à {device_ko3.user}.",
            tested.totp_devices_diagnostic(card_ko3),
        )

        # Several devices exist
        card_ko4 = CarteTOTPFactory(aidant=AidantFactory(username="francois"))
        for _ in range(2):
            TOTPDeviceFactory(key=card_ko4.seed, user=card_ko4.aidant)

        self.assertIn(
            "Il faudrait garder un seul TOTP Device",
            tested.totp_devices_diagnostic(card_ko4),
        )


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
