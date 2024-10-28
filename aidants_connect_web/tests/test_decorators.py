from django.conf import settings
from django.db import transaction
from django.test import TestCase, tag
from django.utils import timezone

from freezegun import freeze_time

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("decorators")
class ActivityRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory()
        device = cls.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")

    def test_activity_required_decorated_page_loads_if_action_just_happened(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertEqual(response.status_code, 200)

    def test_activity_required_decorated_page_redirects_if_action_didnt_just_happened(
        self,
    ):
        self.client.force_login(self.aidant_thierry)
        with freeze_time(timezone.now() + settings.ACTIVITY_CHECK_DURATION):
            self.assertEqual(self.aidant_thierry.is_authenticated, True)
            response = self.client.get("/creation_mandat/")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/activity_check/?next=/creation_mandat/")


@tag("decorators")
class AidantRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory()
        cls.responsable_georges = AidantFactory(
            organisation=cls.aidant_thierry.organisation,
            can_create_mandats=False,
        )
        cls.responsable_georges.responsable_de.add(cls.aidant_thierry.organisation)

    def test_aidant_user_can_access_decorated_page(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertEqual(response.status_code, 200)

    def test_non_aidant_user_cannot_access_decorated_page(self):
        self.client.force_login(self.responsable_georges)
        response = self.client.get("/creation_mandat/")
        self.assertEqual(response.status_code, 302)


@tag("decorators")
class RespoStructureRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory()
        cls.responsable_georges = AidantFactory(
            organisation=cls.aidant_thierry.organisation,
            can_create_mandats=False,
            post__is_organisation_manager=True,
        )
        cls.responsable_georges.responsable_de.add(OrganisationFactory())

    def test_responsable_can_access_decorated_page(self):
        self.client.force_login(self.responsable_georges)
        response = self.client.get("/espace-responsable/organisation/")
        self.assertEqual(response.status_code, 200)

    def test_non_responsable_user_cannot_access_decorated_page(self):
        with self.subTest("Aidant is not referent"):
            self.client.force_login(self.aidant_thierry)
            response = self.client.get("/espace-responsable/organisation/")
            self.assertEqual(response.status_code, 302)

        with self.subTest("Aidant is referent of a different organisation"):
            with transaction.atomic():
                self.aidant_thierry.responsable_de.add(OrganisationFactory())

            self.client.force_login(self.aidant_thierry)
            response = self.client.get("/espace-responsable/organisation/")
            self.assertEqual(response.status_code, 302)
