from django.conf import settings
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_common.utils.constants import JournalActionKeywords
from aidants_connect_web.models import Aidant, Journal
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    OrganisationFactory,
    UsagerFactory,
)
from aidants_connect_web.views import espace_aidant, usagers


@tag("usagers")
class EspaceAidantHomePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory()

    def test_anonymous_user_cannot_access_espace_aidant_view(self):
        response = self.client.get(reverse("espace_aidant_home"))
        self.assertRedirects(response, "/accounts/login/?next=/espace-aidant/")

    def test_espace_aidant_home_url_triggers_the_right_view(self):
        found = resolve(reverse("espace_aidant_home"))
        self.assertEqual(found.func.view_class, espace_aidant.Home)

    def test_espace_aidant_home_url_triggers_the_right_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(reverse("espace_aidant_home"))
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")


@tag("usagers")
class ValidateCGU(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Riri has never validated any CGU
        cls.aidant_riri: Aidant = AidantFactory(username="riri")
        # Fifi has validated previous a previous CGU version
        cls.aidant_fifi: Aidant = AidantFactory(
            username="fifi", validated_cgu_version="0.1"
        )
        # Loulou is up to date
        cls.aidant_loulou: Aidant = AidantFactory(
            username="loulou", validated_cgu_version=settings.CGU_CURRENT_VERSION
        )

    def test_triggers_correct_view(self):
        found = resolve(reverse("espace_aidant_cgu"))
        self.assertEqual(found.func.view_class, espace_aidant.ValidateCGU)

    def test_renders_correct_template(self):
        self.client.force_login(self.aidant_riri)
        response = self.client.get(reverse("espace_aidant_cgu"))
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_aidant/validate_cgu.html"
        )

    def test_must_accept_cgus(self):
        self.client.force_login(self.aidant_riri)
        response = self.client.post(reverse("espace_aidant_cgu"), {"agree": False})
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "Ce champ est obligatoire.",
            response.context_data["form"].errors["agree"][0],
        )

    def test_accepts_cgus(self):
        self.client.force_login(self.aidant_riri)
        self.assertIsNone(self.aidant_riri.validated_cgu_version)
        response = self.client.post(reverse("espace_aidant_cgu"), {"agree": True})
        self.assertIsNone(self.aidant_riri.validated_cgu_version)
        self.assertRedirects(response, reverse("espace_aidant_home"))

    def test_ask_to_validate_cgu_if_no_cgu_validated(self):
        self.client.force_login(self.aidant_riri)
        response = self.client.get("/espace-aidant/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "valider les conditions générales d’utilisation",
            response_content,
            "CGU message is hidden, it should be visible",
        )

    def test_ask_to_validate_cgu_if_obsolete_cgu_validated(self):
        self.client.force_login(self.aidant_fifi)
        response = self.client.get("/espace-aidant/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "valider les conditions générales d’utilisation",
            response_content,
            "CGU message is hidden, it should be visible",
        )

    def test_dont_ask_to_validate_cgu_if_no_need(self):
        self.client.force_login(self.aidant_loulou)
        response = self.client.get("/espace-aidant/")
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "valider les conditions générales d’utilisation",
            response_content,
            "CGU message is shown, it should be hidden",
        )


@tag("usagers")
class SwitchOrganisationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_url = "/espace-aidant/"
        cls.aidant = AidantFactory()

        cls.first_org = OrganisationFactory(name="First")
        cls.second_org = OrganisationFactory(name="Second")
        cls.aidant_with_orgs = AidantFactory(organisation=cls.first_org)
        cls.aidant_with_orgs.organisations.set((cls.first_org, cls.second_org))

    def test_switch_url_triggers_the_right_view(self):
        found = resolve(reverse("espace_aidant_switch_main_organisation"))
        self.assertEqual(found.func.view_class, espace_aidant.SwitchMainOrganisation)

    def test_switch_url_triggers_the_right_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(reverse("espace_aidant_switch_main_organisation"))
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_aidant/switch_main_organisation.html"
        )

    def test_aidant_does_not_see_the_switch_if_they_cannot_change_orgs(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/")
        self.assertNotContains(response, "Changer d'organisation")

    def test_aidant_can_see_the_switch_if_they_can_change_orgs(self):
        self.aidant.organisations.set((self.aidant.organisation, OrganisationFactory()))
        self.client.force_login(self.aidant)
        response = self.client.get("/espace-aidant/")
        self.assertContains(response, "Changer d'organisation")

    def test_aidant_can_switch_to_an_org_they_belong_to(self):
        orgas = self.aidant_with_orgs.organisations.all()
        self.client.force_login(self.aidant_with_orgs)
        self.assertEqual(
            Journal.objects.filter(
                action=JournalActionKeywords.SWITCH_ORGANISATION
            ).count(),
            0,
        )
        response = self.client.post(
            reverse("espace_aidant_switch_main_organisation"),
            {"organisation": orgas[1].id},
        )
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)
        self.aidant_with_orgs.refresh_from_db()
        self.assertEqual(self.aidant_with_orgs.organisation.id, orgas[1].id)
        self.assertEqual(
            Journal.objects.filter(
                action=JournalActionKeywords.SWITCH_ORGANISATION
            ).count(),
            1,
        )

    def test_aidant_cannot_switch_to_an_unexisting_orga(self):
        orgas = self.aidant_with_orgs.organisations.all()
        self.client.force_login(self.aidant_with_orgs)
        response = self.client.post(
            reverse("espace_aidant_switch_main_organisation"),
            {"organisation": 9876543},
        )
        self.assertRedirects(
            response,
            reverse("espace_aidant_switch_main_organisation"),
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("espace_aidant_switch_main_organisation"))
        self.assertContains(response, "Il est impossible")
        self.aidant_with_orgs.refresh_from_db()
        self.assertEqual(self.aidant_with_orgs.organisation.id, orgas[0].id)

    def test_aidant_cannot_switch_to_an_org_they_dont_belong(self):
        orgas = self.aidant_with_orgs.organisations.all()
        unrelated_org = OrganisationFactory(name="Totally unrelated people")
        self.client.force_login(self.aidant_with_orgs)
        response = self.client.post(
            reverse("espace_aidant_switch_main_organisation"),
            {"organisation": unrelated_org.id},
        )
        self.assertRedirects(
            response,
            reverse("espace_aidant_switch_main_organisation"),
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("espace_aidant_switch_main_organisation"))
        self.assertContains(response, "Il est impossible")
        self.assertNotContains(response, unrelated_org.name)
        self.aidant_with_orgs.refresh_from_db()
        self.assertEqual(self.aidant_with_orgs.organisation.id, orgas[0].id)


@tag("usagers")
class UsagersIndexPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory()

    def test_usagers_index_url_triggers_the_usagers_index_view(self):
        found = resolve("/usagers/")
        self.assertEqual(found.func, usagers.usagers_index)

    def test_usagers_index_url_triggers_the_usagers_index_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/usagers/")
        self.assertTemplateUsed(response, "aidants_connect_web/usagers/usagers.html")


@tag("usagers")
class UsagersDetailsPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory()
        cls.other_aidant = AidantFactory()
        cls.usager = UsagerFactory()
        cls.mandat = MandatFactory(
            organisation=cls.aidant.organisation, usager=cls.usager
        )
        AutorisationFactory(mandat=cls.mandat)

    def test_usager_details_url_triggers_the_usager_details_view(self):
        found = resolve(f"/usagers/{self.usager.id}/")
        self.assertIs(found.func.view_class, usagers.UsagerView)

    def test_usager_detail_isnt_visible_for_anonymous_user(self):
        response = self.client.get(f"/usagers/{self.usager.id}/")
        str_redirect = f"{reverse('login')}?next=/usagers/{self.usager.id}/"
        self.assertRedirects(response, str_redirect)

    def test_usager_details_isnt_visible_for_another_aidant(self):
        self.client.force_login(self.other_aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        self.assertTemplateNotUsed(response, "aidants_connect_web/usager_details.html")
        self.assertRedirects(response, reverse("espace_aidant_home"))

    def test_usager_details_url_triggers_the_usager_details_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        self.assertTemplateUsed(response, "aidants_connect_web/usager_details.html")

    def test_usager_details_template_dynamic_title(self):
        self.client.force_login(self.aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        response_content = response.content.decode("utf-8")
        self.assertIn(
            "<title>Aidants Connect - Homer Simpson</title>", response_content
        )

    def test_usager_details_renew_mandat(self):
        self.client.force_login(self.aidant)
        response = self.client.get(f"/usagers/{self.usager.id}/")
        response_content = response.content.decode("utf-8")
        self.assertIn("Renouveler le mandat", response_content)
        self.assertIn(
            reverse("renew_mandat", kwargs={"usager_id": self.usager.id}),
            response_content,
        )


@tag("aidants", "totp")
class LowerTOTPToleranceOnLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory(username="tic")
        cls.other_aidant = AidantFactory(username="tac")

    def create_correct_device(self, aidant):
        correct_device = TOTPDevice(user=aidant, tolerance=0, confirmed=True)
        correct_device.save()

    def create_overtolerant_device(self, aidant):
        tolerant_device = TOTPDevice(user=aidant, tolerance=50, confirmed=True)
        tolerant_device.save()

    def count_overtolerant_devices(self):
        return TOTPDevice.objects.filter(tolerance__gt=1).count()

    def test_login_ok_with_one_overtolerant_device(self):
        self.create_overtolerant_device(self.aidant)
        self.assertEqual(1, self.count_overtolerant_devices())
        self.client.force_login(self.aidant)
        self.assertEqual(0, self.count_overtolerant_devices())

    def test_login_ok_with_several_overtolerant_devices(self):
        for _ in range(5):
            self.create_overtolerant_device(self.aidant)
        self.assertEqual(5, self.count_overtolerant_devices())
        self.client.force_login(self.aidant)
        self.assertEqual(0, self.count_overtolerant_devices())

    def test_login_ok_with_no_overtolerant_device(self):
        self.create_correct_device(self.aidant)
        self.client.force_login(self.aidant)
        self.assertEqual(0, self.count_overtolerant_devices())

    def test_no_other_users_device_is_changed(self):
        self.create_correct_device(self.aidant)
        self.create_overtolerant_device(self.other_aidant)
        self.assertEqual(1, self.count_overtolerant_devices())
        self.client.force_login(self.aidant)
        self.assertEqual(1, self.count_overtolerant_devices())
