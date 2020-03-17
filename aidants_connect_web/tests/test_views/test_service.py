import os

from django.conf import settings
from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from freezegun import freeze_time

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.views import service


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
        self.aidant = AidantFactory()

    def test_journal_records_when_aidant_logs_in(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/dashboard.html")
        self.assertEqual(Journal.objects.count(), 1)
        self.assertEqual(Journal.objects.all()[0].action, "connect_aidant")
        self.client.get("/usagers/")
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
        self.aidant = AidantFactory()

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
class ActivityCheckPageTests(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory()
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")

    def test_totp_url_triggers_totp_view(self):
        found = resolve("/activity_check/")
        self.assertEqual(found.func, service.activity_check)

    def test_totp_url_triggers_totp_template(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/activity_check/")
        self.assertTemplateUsed(response, "registration/activity_check.html")

    def test_totp_page_with_resolvable_next_redirects(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/activity_check/?next=/creation_mandat/", data={"otp_token": "123456"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/creation_mandat/")

    def test_totp_page_with_non_resolvable_next_triggers_404(self):
        # test with get
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/activity_check/?next=http://myfishingsite.com")
        self.assertEqual(response.status_code, 404)
        # get with post
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/activity_check/?next=http://myfishingsite.com",
            data={"otp_token": "123456"},
        )
        self.assertEqual(response.status_code, 404)

    def test_successful_totp_check_creates_journal_entry(self):
        self.client.force_login(self.aidant_thierry)
        self.assertEqual(Journal.objects.count(), 1)
        with freeze_time(timezone.now() + settings.ACTIVITY_CHECK_DURATION):
            response = self.client.post(
                "/activity_check/?next=/usagers/1/?a=test", data={"otp_token": "123456"}
            )
            self.assertEqual(Journal.objects.count(), 2)
            self.assertEqual(Journal.objects.last().action, "activity_check_aidant")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/usagers/1/?a=test")


@tag("service")
class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")


@tag("service")
class StatistiquesTests(TestCase):
    def test_stats_url_triggers_the_statistiques_view(self):
        found = resolve("/stats/")
        self.assertEqual(found.func, service.statistiques)

    def test_stats_url_triggers_the_statistiques_template(self):
        response = self.client.get("/stats/")
        self.assertTemplateUsed(response, "footer/statistiques.html")


@tag("service")
class MentionsLegalesTests(TestCase):
    def test_mentions_legales_url_triggers_the_correct_view(self):
        found = resolve("/mentions-legales/")
        self.assertEqual(found.func, service.mentions_legales)

    def test_stats_url_triggers_the_correct_template(self):
        response = self.client.get("/mentions-legales/")
        self.assertTemplateUsed(response, "footer/mentions_legales.html")


@tag("service")
class CguTests(TestCase):
    def test_stats_url_triggers_the_cgu_view(self):
        found = resolve("/cgu/")
        self.assertEqual(found.func, service.cgu)

    def test_stats_url_triggers_the_cgu_template(self):
        response = self.client.get("/cgu/")
        self.assertTemplateUsed(response, "footer/cgu.html")


@tag("service")
class GuideUtilisationTests(TestCase):
    def test_guide_utilisation_url_triggers_the_correct_view(self):
        found = resolve("/guide_utilisation/")
        self.assertEqual(found.func, service.guide_utilisation)

    def test_stats_url_triggers_the_correct_template(self):
        response = self.client.get("/guide_utilisation/")
        self.assertTemplateUsed(response, "aidants_connect_web/guide_utilisation.html")
