import os

from django.test.client import Client
from django.test import TestCase, tag
from django.urls import resolve
from django.conf import settings

from aidants_connect_web.views import service
from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import UserFactory

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("service")
class HomePageTests(TestCase):
    def test_root_url_triggers_the_homepage_view(self):
        found = resolve("/")
        self.assertEqual(found.func, service.home_page)

    def test_root_url_triggers_the_homepage_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "aidants_connect_web/home_page.html")


@tag("service")
class LoginPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = UserFactory()

    def test_journal_records_when_aidant_logs_in(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/dashboard.html")
        self.assertEqual(Journal.objects.count(), 1)
        self.assertEqual(Journal.objects.all()[0].action, "connect_aidant")
        self.client.get("/mandats/")
        self.assertEqual(Journal.objects.count(), 1)

    def test_login_view_redirects_to_next_if_aidant_is_authenticated(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get("/accounts/login/?next=/dashboard/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/dashboard.html")


@tag("service")
class LogoutPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = UserFactory()

    def test_logout_url_triggers_the_logout_view(self):
        found = resolve("/logout/")
        self.assertEqual(found.func, service.logout_page)

    def test_logout_url_triggers_loging_if_not_logged_in(self):
        response = self.client.get("/logout/")
        self.assertRedirects(response, "/accounts/login/?next=/logout/")

    def test_logout_url_triggers_home_page_if_logged_in(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/logout/")
        self.assertRedirects(response, "/")


@tag("service")
class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")
