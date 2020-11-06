import os
from datetime import datetime

from django.conf import settings
from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from freezegun import freeze_time

from aidants_connect_web.models import Journal, Organisation
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    OrganisationFactory,
    UsagerFactory,
)
from aidants_connect_web.views import service


fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("service")
class HomePageTests(TestCase):
    def test_root_url_triggers_the_homepage_view(self):
        found = resolve("/")
        self.assertEqual(found.func, service.home_page)

    def test_root_url_triggers_the_homepage_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "public_website/home_page.html")


@tag("service")
class LoginPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = AidantFactory()

    def test_journal_records_when_aidant_logs_in(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get("/espace-aidant/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")
        self.assertEqual(Journal.objects.count(), 1)
        self.assertEqual(Journal.objects.all()[0].action, "connect_aidant")
        self.client.get("/usagers/")
        self.assertEqual(Journal.objects.count(), 1)

    def test_login_view_redirects_to_next_if_aidant_is_authenticated(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get("/accounts/login/?next=/espace-aidant/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")


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
        self.assertTemplateUsed(response, "login/activity_check.html")

    def test_totp_page_with_resolvable_next_redirects(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/activity_check/?next=/creation_mandat/", data={"otp_token": "123456"},
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
class EnvironmentVariablesTests(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")


@tag("service")
class StatistiquesTests(TestCase):
    def setUp(self):
        mairie_de_houlbec = OrganisationFactory()
        aidant_thierry = AidantFactory()
        usager_homer = UsagerFactory()
        mandat_houlbec_homer = MandatFactory(
            organisation=mairie_de_houlbec, usager=usager_homer
        )
        autorisation_justice_houlbec_homer = AutorisationFactory(
            mandat=mandat_houlbec_homer
        )

        Journal.objects.create(
            aidant=aidant_thierry,
            usager=usager_homer,
            action="use_autorisation",
            demarche="justice",
            autorisation=autorisation_justice_houlbec_homer.id,
        )
        Journal.objects.create(
            aidant=aidant_thierry,
            usager=usager_homer,
            action="use_autorisation",
            demarche="justice",
            autorisation=autorisation_justice_houlbec_homer.id,
        )

        # An Aidant from Stafforg is among us !
        staff_organisation = Organisation.objects.create(
            name=settings.STAFF_ORGANISATION_NAME
        )
        aidant_staff_organisation = AidantFactory(
            username="test@user.domain", organisation=staff_organisation
        )

        # an aidant staff_organisation has an attestation
        # with an usager also helped by another aidant

        mandat_stafforg_homer = MandatFactory(
            organisation=staff_organisation, usager=usager_homer
        )
        autorisation_justice_stafforg_homer = AutorisationFactory(
            mandat=mandat_stafforg_homer
        )

        Journal.objects.create(
            aidant=aidant_staff_organisation,
            usager=usager_homer,
            action="use_autorisation",
            demarche="justice",
            autorisation=autorisation_justice_stafforg_homer.id,
        )
        # An aidant staff_organisation has an exclusive autorisation with a user
        usager_laurent = UsagerFactory(given_name="Laurent", sub="sub for laurent")

        mandat_stafforg_laurent = MandatFactory(
            organisation=staff_organisation, usager=usager_homer
        )
        autorisation_justice_stafforg_laurent = AutorisationFactory(
            mandat=mandat_stafforg_laurent,
        )

        Journal.objects.create(
            action="use_autorisation",
            aidant=aidant_staff_organisation,
            usager=usager_laurent,
            demarche="justice",
            autorisation=autorisation_justice_stafforg_laurent.id,
        )

        # jacqueline has an expired autorisation and no active autorisations
        usager_jacqueline = UsagerFactory(
            given_name="Jacqueline",
            creation_date=datetime(year=2000, month=1, day=1, tzinfo=timezone.utc),
            sub="new_sub_for_jacqueline",
        )
        mandat_houlbec_jacqueline = MandatFactory(
            organisation=mairie_de_houlbec,
            usager=usager_jacqueline,
            expiration_date=datetime(year=2000, month=1, day=1, tzinfo=timezone.utc),
        )

        autorisation_justice_houlbec_jacqueline = AutorisationFactory(
            mandat=mandat_houlbec_jacqueline,
        )

        Journal.objects.create(
            action="use_autorisation",
            aidant=aidant_thierry,
            usager=usager_jacqueline,
            demarche=autorisation_justice_houlbec_jacqueline.demarche,
            duree=1,
            autorisation=autorisation_justice_houlbec_jacqueline.id,
        )
        Journal.objects.filter(usager=usager_jacqueline).update(
            creation_date=datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)
        )

    def test_stats_url_triggers_the_statistiques_view(self):
        found = resolve("/stats/")
        self.assertEqual(found.func, service.statistiques)

    def test_stats_url_triggers_the_statistiques_template(self):
        response = self.client.get("/stats/")
        self.assertTemplateUsed(response, "public_website/statistiques.html")

    def test_stats_show_the_correct_number_of_aidants_non_staff_organisation(self):
        # aidants should be non-staff_organisation
        response = self.client.get("/stats/")
        self.assertEqual(response.context["aidants_count"], 1)

    def test_stats_show_the_correct_number_of_mandats_non_staff_organisation(self):
        # mandats should be non-staff_organisation and active
        response = self.client.get("/stats/")
        self.assertEqual(response.context["mandats_count"], 2)
        self.assertEqual(response.context["active_mandats_count"], 1)

    def test_usager_without_recent_mandat_are_not_counted_as_recent(self):
        # Usagers should be non-staff_organisation related and if current,
        # should have been created recenlty
        response = self.client.get("/stats/")
        self.assertEqual(response.context["usagers_with_mandat_count"], 2)
        self.assertEqual(response.context["usagers_with_active_mandat_count"], 1)

    def test_old_autorisation_use_are_not_counted_as_recent(self):
        response = self.client.get("/stats/")
        self.assertEqual(response.context["autorisation_use_count"], 3)
        self.assertEqual(response.context["autorisation_use_recent_count"], 2)

    def test_usager_helped_a_long_time_ago_not_counted_as_recent(self):
        # "statistiques_demarches": demarches_aggregation,
        response = self.client.get("/stats/")
        self.assertEqual(response.context["usagers_helped_count"], 2)
        self.assertEqual(response.context["usagers_helped_recent_count"], 1)

    def test_all_help_is_counted_for_demarche_stat_except_staff_organisation(self):
        # "statistiques_demarches"is sorted from most to least popular
        response = self.client.get("/stats/")
        self.assertEqual(response.context["demarches_count"][0]["value"], 3)
        self.assertEqual(response.context["demarches_count"][1]["value"], 0)


@tag("service")
class MentionsLegalesTests(TestCase):
    def test_mentions_legales_url_triggers_the_correct_view(self):
        found = resolve("/mentions-legales/")
        self.assertEqual(found.func, service.mentions_legales)

    def test_stats_url_triggers_the_correct_template(self):
        response = self.client.get("/mentions-legales/")
        self.assertTemplateUsed(response, "public_website/mentions_legales.html")


@tag("service")
class CguTests(TestCase):
    def test_stats_url_triggers_the_cgu_view(self):
        found = resolve("/cgu/")
        self.assertEqual(found.func, service.cgu)

    def test_stats_url_triggers_the_cgu_template(self):
        response = self.client.get("/cgu/")
        self.assertTemplateUsed(response, "public_website/cgu.html")


@tag("service")
class GuideUtilisationTests(TestCase):
    def test_guide_utilisation_url_triggers_the_correct_view(self):
        found = resolve("/guide_utilisation/")
        self.assertEqual(found.func, service.guide_utilisation)

    def test_stats_url_triggers_the_correct_template(self):
        response = self.client.get("/guide_utilisation/")
        self.assertTemplateUsed(response, "public_website/guide_utilisation.html")


@tag("service")
class FAQTests(TestCase):
    def test_faq_url_triggers_the_correct_view(self):
        found = resolve("/faq/")
        self.assertEqual(found.func, service.faq_generale)

    def test_faq_url_triggers_the_correct_template(self):
        response = self.client.get("/faq/")
        self.assertTemplateUsed(response, "public_website/faq/generale.html")
