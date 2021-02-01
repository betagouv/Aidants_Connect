from admin_honeypot.models import LoginAttempt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, tag, TestCase
from django.test.client import Client
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.admin import VisibleToAdminMetier
from aidants_connect_web.admin import VisibleToTechAdmin

from aidants_connect_web.models import (
    Aidant,
    Connection,
    Journal,
    Mandat,
    Organisation,
    Usager,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
)


@tag("admin")
class LoginAttemptAdminPageTests(TestCase):

    def test_honeypot_login_attempt_fails_gracefuly(self):
        login_attempt_id = LoginAttempt.objects.create(username="test").pk
        path = reverse('admin:admin_honeypot_loginattempt_change',
                       args=(login_attempt_id,))
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
        user = AidantFactory(is_staff=True,
                             is_superuser=True)
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
        user = AidantFactory(is_staff=True,
                             is_superuser=False)
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
        user = AidantFactory(is_staff=True,
                             is_superuser=True)
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
        user = AidantFactory(is_staff=True,
                             is_superuser=False)
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
    only_by_atac_models = [Mandat,
                           Usager, Connection, Journal]
    amac_models = [Organisation, Aidant, StaticDevice, TOTPDevice]

    def setUp(self):
        self.amac_user = AidantFactory(username="amac@email.com",
                                       email="amac@email.com",
                                       is_staff=True,
                                       is_superuser=False)
        self.amac_user.set_password("password")
        self.amac_user.save()
        amac_device = StaticDevice.objects.create(user=self.amac_user, name="Device")

        self.amac_client = Client()
        self.amac_client.force_login(self.amac_user)
        # we need do this :
        # https://docs.djangoproject.com/en/3.1/topics/testing/tools/#django.test.Client.session
        amac_session = self.amac_client.session
        amac_session[DEVICE_ID_SESSION_KEY] = amac_device.persistent_id
        amac_session.save()

        self.atac_user = AidantFactory(username="atac@email.com",
                                       email="atac@email.com",
                                       is_staff=True,
                                       is_superuser=True)
        self.atac_user.set_password("password")
        self.atac_user.save()
        atac_device = StaticDevice.objects.create(user=self.atac_user, name="Device")

        self.atac_client = Client()
        self.atac_client.force_login(self.atac_user)
        # we need do this :
        # https://docs.djangoproject.com/en/3.1/topics/testing/tools/#django.test.Client.session
        atac_session = self.atac_client.session
        atac_session[DEVICE_ID_SESSION_KEY] = atac_device.persistent_id
        atac_session.save()

    def test_views_visible_only_by_atac_dont_visible_by_amac_users(self):
        for model in self.only_by_atac_models:
            url_root = f'admin:{model._meta.app_label}_{model.__name__.lower()}'
            list_url = reverse(url_root + '_changelist')
            response = self.amac_client.get(list_url)
            self.assertEqual(response.status_code, 403)

    def test_views_visible_only_by_atac_were_visible_by_atac_users(self):
        for model in self.only_by_atac_models:
            url_root = f'admin:{model._meta.app_label}_{model.__name__.lower()}'
            list_url = reverse(url_root + '_changelist')
            response = self.atac_client.get(list_url)
            self.assertEqual(response.status_code, 200)

    def test_views_visible_by_amac_were_visible_by_amac_users(self):
        for model in self.amac_models:
            url_root = f'admin:{model._meta.app_label}_{model.__name__.lower()}'
            list_url = reverse(url_root + '_changelist')
            response = self.amac_client.get(list_url)
            self.assertEqual(response.status_code, 200)

    def test_views_visible_by_amac_were_visible_by_atac_users(self):
        for model in self.amac_models:
            url_root = f'admin:{model._meta.app_label}_{model.__name__.lower()}'
            list_url = reverse(url_root + '_changelist')
            response = self.atac_client.get(list_url)
            self.assertEqual(response.status_code, 200)


@tag("admin")
class JournalAdminPageTests(TestCase):
    def setUp(self):
        self.atac_user = AidantFactory(username="atac@email.com",
                                       email="atac@email.com",
                                       is_staff=True,
                                       is_superuser=True)
        self.atac_user.set_password("password")
        self.atac_user.save()
        self.atac_device = StaticDevice.objects.create(user=self.atac_user,
                                                       name="Device")

        self.atac_client = Client()
        self.atac_client.force_login(self.atac_user)
        atac_session = self.atac_client.session
        atac_session[DEVICE_ID_SESSION_KEY] = self.atac_device.persistent_id
        atac_session.save()
        url_root = f'admin:{Journal._meta.app_label}_{Journal.__name__.lower()}'
        self.url_root = url_root

    def test_cant_delete_journal_by_admin_views(self):
        self.assertEqual(Journal.objects.count(), 1)
        journal = Journal.objects.all()[0]
        url = reverse(self.url_root + '_delete', args=(journal.pk,))
        response = self.atac_client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_cant_add_journal_by_admin_views(self):
        url = reverse(self.url_root + '_add')
        response = self.atac_client.get(url)
        self.assertEqual(response.status_code, 403)
