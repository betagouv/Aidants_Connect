from datetime import timedelta

from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse
from django.utils.timezone import now

from aidants_connect_common.models import Formation
from aidants_connect_common.tests.factories import (
    FormationFactory,
    FormationOrganizationFactory,
)


@tag("formation")
class ListingFormationsPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.formation_ok: Formation = FormationFactory(
            type_label="Des formations et des Hommes",
            start_datetime=now() + timedelta(days=50),
            organisation=FormationOrganizationFactory(name="Organisation_Formation_OK"),
        )

        cls.formation_too_close: Formation = FormationFactory(
            type_label="À la Bonne Formation", start_datetime=now() + timedelta(days=1)
        )

    def test_listing_formations_page(self):
        response = self.client.get(reverse("listing_formations"))
        self.assertTemplateUsed(response, "public_website/listing_formations.html")
        self.assertContains(response, "Organisation_Formation_OK")
        self.assertNotContains(response, "À la Bonne Formation")
