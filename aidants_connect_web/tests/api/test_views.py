import json
from typing import List

from django.urls import reverse

from rest_framework.test import APITestCase

from aidants_connect_web.models import Organisation
from aidants_connect_web.tests.factories import OrganisationFactory


class OrganisationViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orgas: List[Organisation] = [OrganisationFactory(is_active=False)] + list(
            sorted([OrganisationFactory() for _ in range(8)], key=lambda i: i.pk)
        )

    def test_list_post_disallowed(self):
        response = self.client.post(reverse("organisation-list"), {}, format="json")
        self.assertEqual(405, response.status_code)
        self.assertDictEqual(
            {"detail": "Méthode « POST » non autorisée."},
            json.loads(response.content),
        )

    def test_list_get_paginated(self):
        self.maxDiff = None

        response = self.client.get(reverse("organisation-list"), {}, format="json")
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "count": 8,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(orga.uuid),
                        "url": (
                            "http://testserver"
                            + reverse("organisation-detail", args=(orga.uuid,))
                        ),
                        "pivot": orga.siret,
                        "nom": orga.name,
                        "commune": orga.city,
                        "date_de_creation": (
                            f"{orga.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "date_de_modification": (
                            f"{orga.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "code_postal": orga.zipcode,
                        "code_insee": orga.city_insee_code,
                        "adresse": orga.address,
                        "address_complement": orga.address_complement,
                        "service": (
                            "Réaliser des démarches administratives "
                            "avec un accompagnement"
                        ),
                    }
                    for orga in self.orgas[1:]
                ],
            },
            json.loads(response.content),
        )

    def test_detail_post_disallowed(self):
        response = self.client.post(
            reverse("organisation-detail", args=(self.orgas[0].uuid,)),
            {},
            format="json",
        )
        self.assertEqual(405, response.status_code)
        self.assertDictEqual(
            {"detail": "Méthode « POST » non autorisée."},
            json.loads(response.content),
        )

    def test_detail_get_paginated(self):
        self.maxDiff = None
        response = self.client.get(
            reverse("organisation-detail", args=(self.orgas[1].uuid,)),
            {},
            format="json",
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "id": str(self.orgas[1].uuid),
                "url": (
                    "http://testserver"
                    + reverse("organisation-detail", args=(self.orgas[1].uuid,))
                ),
                "nom": self.orgas[1].name,
                "commune": self.orgas[1].city,
                "date_de_creation": (
                    f"{self.orgas[1].created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                ),
                "date_de_modification": (
                    f"{self.orgas[1].updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                ),
                "pivot": self.orgas[1].siret,
                "code_postal": self.orgas[1].zipcode,
                "code_insee": self.orgas[1].city_insee_code,
                "adresse": self.orgas[1].address,
                "address_complement": self.orgas[1].address_complement,
                "service": (
                    "Réaliser des démarches administratives avec un accompagnement"
                ),
            },
            json.loads(response.content),
        )
