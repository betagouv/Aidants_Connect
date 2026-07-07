import os
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils import timezone

from freezegun import freeze_time

from aidants_connect_common.constants import AuthorizationDurationChoices
from aidants_connect_web.models import AidantStatistiques, Journal, Organisation
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    CarteTOTPFactory,
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
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory()

    def test_journal_records_when_aidant_logs_in(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get(reverse("espace_aidant:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")
        self.assertEqual(Journal.objects.count(), 1)
        self.assertEqual(Journal.objects.all()[0].action, "connect_aidant")
        self.client.get(reverse("espace_aidant:usagers"))
        self.assertEqual(Journal.objects.count(), 1)

    def test_login_view_redirects_to_next_if_aidant_is_authenticated(self):
        self.assertEqual(len(Journal.objects.all()), 0)
        self.client.force_login(self.aidant)
        response = self.client.get(
            f"{reverse('login')}?{urlencode({'next': reverse('espace_aidant:home')})}",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")


@tag("service")
class LogoutPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory()

    def test_logout_url_triggers_the_logout_view(self):
        found = resolve("/logout-session/")
        self.assertEqual(found.func, service.logout_page)

    def test_logout_url_triggers_loging_if_not_logged_in(self):
        response = self.client.get("/logout-session/")
        self.assertRedirects(response, "/accounts/login/?next=/logout-session/")

    def test_logout_url_triggers_home_page_if_logged_in(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/logout-session/")
        self.assertRedirects(response, "/")


@tag("service")
class ActivityCheckPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory()
        device = cls.aidant_thierry.staticdevice_set.create(id=1)
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
            f"/activity_check/?{urlencode({'next': reverse('espace_aidant:new_mandat')})}",  # noqa: E501
            data={"otp_token": "123456"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("espace_aidant:new_mandat"))

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
            next_usager = (
                reverse("espace_aidant:usager_details", kwargs={"usager_id": 1})
                + "?a=test"
            )
            response = self.client.post(
                f"/activity_check/?{urlencode({'next': next_usager})}",
                data={"otp_token": "123456"},
            )
            self.assertEqual(Journal.objects.count(), 2)
            self.assertEqual(Journal.objects.last().action, "activity_check_aidant")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, next_usager)


@tag("service")
class EnvironmentVariablesTests(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")


@tag("service")
class StatistiquesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        mairie_de_houlbec = OrganisationFactory()
        aidant_thierry = AidantFactory()
        carte = CarteTOTPFactory(aidant=aidant_thierry)
        carte.get_or_create_totp_device()
        usager_homer = UsagerFactory()
        mandat_houlbec_homer = MandatFactory(
            organisation=mairie_de_houlbec, usager=usager_homer
        )
        autorisation_justice_houlbec_homer = AutorisationFactory(
            mandat=mandat_houlbec_homer
        )

        Journal.objects.create(
            aidant=aidant_thierry,
            organisation=aidant_thierry.organisation,
            usager=usager_homer,
            action="use_autorisation",
            demarche="justice",
            autorisation=autorisation_justice_houlbec_homer.id,
        )
        Journal.objects.create(
            aidant=aidant_thierry,
            organisation=aidant_thierry.organisation,
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
        CarteTOTPFactory(aidant=aidant_staff_organisation)

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
            organisation=aidant_staff_organisation.organisation,
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
            organisation=aidant_staff_organisation.organisation,
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
            organisation=aidant_thierry.organisation,
            usager=usager_jacqueline,
            demarche=autorisation_justice_houlbec_jacqueline.demarche,
            duree=1,
            autorisation=autorisation_justice_houlbec_jacqueline.id,
        )
        Journal.objects.filter(usager=usager_jacqueline).update(
            creation_date=datetime(year=2000, month=1, day=1, tzinfo=timezone.utc)
        )

    def test_stats_url_triggers_the_statistiques_view(self):
        found = resolve(reverse("statistiques"))
        self.assertEqual(found.func.view_class, service.StatistiquesView)

    def test_stats_url_triggers_the_statistiques_template(self):
        response = self.client.get(reverse("statistiques"))
        self.assertTemplateUsed(response, "public_website/statistiques.html")

    def test_stats_show_the_correct_number_of_aidants_non_staff_organisation(self):
        # aidants should be non-staff_organisation
        response = self.client.get(reverse("statistiques"))
        self.assertEqual(
            response.context["usage_section"]["Aidants habilités"],
            1,
            "Should count aidant_thierry alone",
        )
        self.assertEqual(
            response.context["usage_section"]["Structures habilitées"],
            1,
            "Should count aidant_thierry's organisation alone",
        )

    def test_stats_show_the_correct_number_of_mandats_non_staff_organisation(self):
        # mandats should be non-staff_organisation and active
        response = self.client.get(reverse("statistiques"))
        self.assertEqual(response.context["usage_section"]["Mandats créés"], 2)
        self.assertEqual(response.context["usage_section"]["Mandats actifs"], 1)
        self.assertEqual(
            len(response.context["mandats_evolution_data"]["labels"]),
            24,
        )
        self.assertEqual(
            len(response.context["demarches_evolution_data"]["labels"]),
            24,
        )
        self.assertEqual(
            len(response.context["operational_aidants_evolution_data"]["labels"]),
            24,
        )

    @freeze_time("2026-06-15")
    def test_operational_aidants_evolution_uses_snapshots(self):
        # One snapshot in 2026-04
        with freeze_time("2026-04-10"):
            AidantStatistiques.objects.create(number_aidant_can_create_mandat=3)
        # Two snapshots in 2026-05: the latest of the month must win
        with freeze_time("2026-05-05"):
            AidantStatistiques.objects.create(number_aidant_can_create_mandat=5)
        with freeze_time("2026-05-20"):
            AidantStatistiques.objects.create(number_aidant_can_create_mandat=7)

        response = self.client.get(reverse("statistiques"))
        data = response.context["operational_aidants_evolution_data"]

        self.assertEqual(len(data["labels"]), 24)
        # Last complete month is 2026-05 (current month excluded)
        self.assertEqual(data["labels"][-1], "05/2026")
        self.assertEqual(data["values"][-1], 7)
        # 2026-04 keeps its own snapshot value
        self.assertEqual(data["labels"][-2], "04/2026")
        self.assertEqual(data["values"][-2], 3)
        # 2026-03 has no earlier snapshot to forward-fill from
        self.assertEqual(data["labels"][-3], "03/2026")
        self.assertEqual(data["values"][-3], 0)
        # The line is the cumulative stock (same as the snapshot level)
        self.assertEqual(data["cumulative"], data["values"])
        # The bars are the month-over-month increase derived from the level
        self.assertEqual(data["monthly"][-1], 4)
        self.assertEqual(data["monthly"][-2], 3)
        self.assertEqual(data["monthly"][-3], 0)

    @freeze_time("2026-06-15")
    def test_mandats_evolution_exposes_monthly_and_cumulative(self):
        orga = OrganisationFactory()
        # Two mandats before the 24-month window feed the cumulative baseline
        for _ in range(2):
            MandatFactory(
                organisation=orga,
                usager=UsagerFactory(),
                creation_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
        # One mandat during the last complete month (2026-05)
        MandatFactory(
            organisation=orga,
            usager=UsagerFactory(),
            creation_date=datetime(2026, 5, 10, tzinfo=timezone.utc),
        )

        response = self.client.get(reverse("statistiques"))
        data = response.context["mandats_evolution_data"]

        self.assertEqual(data["labels"][-1], "05/2026")
        # Monthly flow only counts the event of that month
        self.assertEqual(data["monthly"][-1], 1)
        # Cumulative includes the two pre-window mandats as a baseline
        self.assertEqual(data["cumulative"][-1], data["cumulative"][-2] + 1)
        self.assertGreaterEqual(data["cumulative"][0], 2)
        # Cumulative is monotonically non-decreasing
        self.assertEqual(data["cumulative"], sorted(data["cumulative"]))

    def test_usager_helped_a_long_time_ago_not_counted_as_recent(self):
        # "statistiques_demarches": demarches_aggregation,
        response = self.client.get(reverse("statistiques"))
        self.assertEqual(response.context["usage_section"]["Démarches réalisées"], 3)
        self.assertEqual(response.context["usage_section"]["Personnes accompagnées"], 2)

    def test_all_help_is_counted_for_demarche_stat_except_staff_organisation(self):
        # "statistiques_demarches"is sorted from most to least popular
        response = self.client.get(reverse("statistiques"))
        self.assertEqual(response.context["data"]["values"][0], 3)
        self.assertEqual(response.context["data"]["values"][1], 0)

    def test_stats_show_mandat_durees_distribution(self):
        response = self.client.get(reverse("statistiques"))
        mandat_durees_data = response.context["mandat_durees_data"]
        self.assertEqual(
            mandat_durees_data["titles"][0],
            AuthorizationDurationChoices.SHORT.label,
        )
        self.assertEqual(mandat_durees_data["values"][0], 2)
        self.assertEqual(
            sum(mandat_durees_data["values"]),
            response.context["usage_section"]["Mandats créés"],
        )

    def test_stats_page_includes_demarches_realisees_info(self):
        response = self.client.get(reverse("statistiques"))
        self.assertIsNotNone(response.context["demarches_realisees_since_date"])
        self.assertContains(response, "demarches-realisees-usage-info")
        self.assertContains(
            response,
            "Connexions réalisées via Aidants Connect - pour suivre et réaliser une ou plusieurs démarches administratives",  # noqa: E501
        )

    def test_stats_page_includes_demarche_type_info(self):
        response = self.client.get(reverse("statistiques"))
        self.assertContains(response, "demarche-type-info")
        self.assertContains(
            response,
            "Domaine déclaré par l'aidant à l'utilisation du mandat",
        )


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
    def test_guide_utilisation_url_redirects_to_docs(self):
        response = self.client.get("/guide_utilisation/")
        self.assertRedirects(
            response,
            "https://docs.numerique.gouv.fr/docs/6d7aa937-9030-4af4-9522-3a725ceda6da/",
            status_code=301,
            fetch_redirect_response=False,
        )
