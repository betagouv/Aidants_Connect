from django.conf import settings
from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve, reverse

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
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
        response = self.client.get("/espace-aidant/")
        self.assertRedirects(response, "/accounts/login/?next=/espace-aidant/")

    def test_espace_aidant_home_url_triggers_the_right_view(self):
        found = resolve("/espace-aidant/")
        self.assertEqual(found.func, espace_aidant.home)

    def test_espace_aidant_home_url_triggers_the_right_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get("/espace-aidant/")
        self.assertTemplateUsed(response, "aidants_connect_web/espace_aidant/home.html")


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
        self.assertTemplateUsed(response, "aidants_connect_web/usagers.html")


@tag("usagers")
class UsagersDetailsPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant = AidantFactory()
        cls.usager = UsagerFactory()
        cls.mandat = MandatFactory(
            organisation=cls.aidant.organisation, usager=cls.usager
        )
        AutorisationFactory(mandat=cls.mandat)

    def test_usager_details_url_triggers_the_usager_details_view(self):
        found = resolve(f"/usagers/{self.usager.id}/")
        self.assertEqual(found.func, usagers.usager_details)

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
        self.assertIn(reverse("renew_mandat", args=(self.usager.pk,)), response_content)


@tag("responsable-structure")
class InsistOnValidatingCGUsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Riri has never validated any CGU
        cls.aidant_riri = AidantFactory(username="riri")
        # Fifi has validated previous a previous CGU version
        cls.aidant_fifi = AidantFactory(username="fifi", validated_cgu_version="0.1")
        # Loulou is up to date
        cls.aidant_loulou = AidantFactory(
            username="loulou", validated_cgu_version=settings.CGU_CURRENT_VERSION
        )

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
