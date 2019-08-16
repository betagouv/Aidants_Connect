import os

from django.test.client import Client
from django.test import TestCase
from django.urls import resolve
from django.conf import settings

from aidants_connect_web.views import service
from aidants_connect_web.models import Aidant

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


class HomePageTests(TestCase):
    def test_root_url_triggers_the_homepage_view(self):
        found = resolve("/")
        self.assertEqual(found.func, service.home_page)

    def test_root_url_triggers_the_homepage_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "aidants_connect_web/home_page.html")


class LogoutPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = Aidant.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )

    def test_logout_url_triggers_the_logout_view(self):
        found = resolve("/logout/")
        self.assertEqual(found.func, service.logout_page)

    def test_logout_url_triggers_loging_if_not_logged_in(self):
        response = self.client.get("/logout/")
        self.assertRedirects(response, "/accounts/login/?next=/logout/")

    def test_logout_url_triggers_home_page_if_logged_in(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        response = self.client.get("/logout/")
        self.assertRedirects(response, "/")


class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")
