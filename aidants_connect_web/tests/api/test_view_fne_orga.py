import json

from django.urls import reverse

from rest_framework.test import APITestCase

from aidants_connect_web.models import Organisation
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


class FNEOrganisationViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orgas = [OrganisationFactory(name="INACTIVE ORGA", is_active=False)] + list(
            sorted([OrganisationFactory() for _ in range(8)], key=lambda i: i.pk)
        )

        orga_user = OrganisationFactory(name="ORGA USER")
        cls.root = AidantFactory(username="root@root.fr", organisation=orga_user)
        cls.orgas.append(cls.root.organisation)

    def test_list_post_disallowed(self):
        self.client.force_login(self.root)
        response = self.client.post(
            reverse("fne_organisations-list"), {}, format="json"
        )
        self.assertEqual(405, response.status_code)
        self.assertDictEqual(
            {"detail": "Méthode « POST » non autorisée."},
            json.loads(response.content),
        )

    def test_list_get_paginated(self):
        self.maxDiff = None
        self.client.force_login(self.root)

        response = self.client.get(reverse("fne_organisations-list"), {}, format="json")
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "count": 10,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": orga.id,
                        "uuid": str(orga.uuid),
                        "url": (
                            "http://testserver"
                            + reverse("fne_organisations-detail", args=(orga.uuid,))
                        ),
                        "is_active": orga.is_active,
                        "name": orga.name,
                        "city": orga.city,
                        "created_at": (
                            f"{orga.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "updated_at": (
                            f"{orga.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "zipcode": orga.zipcode,
                        "siret": orga.siret,
                        "city_insee_code": orga.city_insee_code,
                        "address": orga.address,
                        "address_complement": orga.address_complement,
                        "num_mandats": orga.num_mandats,
                        "france_services_label": orga.france_services_label,
                        "france_services_number": orga.france_services_number,
                    }
                    for orga in self.orgas
                ],
            },
            json.loads(response.content),
        )

    def test_detail_post_disallowed(self):
        self.client.force_login(self.root)
        response = self.client.post(
            reverse("fne_organisations-detail", args=(self.orgas[0].uuid,)),
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
        self.client.force_login(self.root)
        response = self.client.get(
            reverse("fne_organisations-detail", args=(self.orgas[1].uuid,)),
            {},
            format="json",
        )
        self.assertEqual(200, response.status_code)
        orga = self.orgas[1]
        self.assertDictEqual(
            {
                "id": orga.id,
                "uuid": str(orga.uuid),
                "url": (
                    "http://testserver"
                    + reverse("fne_organisations-detail", args=(orga.uuid,))
                ),
                "is_active": orga.is_active,
                "name": orga.name,
                "city": orga.city,
                "created_at": (f"{orga.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"),
                "updated_at": (f"{orga.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"),
                "zipcode": orga.zipcode,
                "siret": orga.siret,
                "city_insee_code": orga.city_insee_code,
                "address": orga.address,
                "address_complement": orga.address_complement,
                "num_mandats": orga.num_mandats,
                "france_services_label": orga.france_services_label,
                "france_services_number": orga.france_services_number,
            },
            json.loads(response.content),
        )

    def test_filter_orga_siret(self):
        orga = Organisation.objects.all().first()
        orga.siret = 11111111111111
        orga.save()

        self.maxDiff = None
        self.client.force_login(self.root)

        response = self.client.get(
            reverse("fne_organisations-list"), {"siret": 11111111111111}, format="json"
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": orga.id,
                        "uuid": str(orga.uuid),
                        "url": (
                            "http://testserver"
                            + reverse("fne_organisations-detail", args=(orga.uuid,))
                        ),
                        "is_active": orga.is_active,
                        "name": orga.name,
                        "city": orga.city,
                        "created_at": (
                            f"{orga.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "updated_at": (
                            f"{orga.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "zipcode": orga.zipcode,
                        "siret": orga.siret,
                        "city_insee_code": orga.city_insee_code,
                        "address": orga.address,
                        "address_complement": orga.address_complement,
                        "num_mandats": orga.num_mandats,
                        "france_services_label": orga.france_services_label,
                        "france_services_number": orga.france_services_number,
                    }
                    for orga in Organisation.objects.filter(pk=orga.pk)
                ],
            },
            json.loads(response.content),
        )

    def test_filter_orga_created_at(self):
        orga = Organisation.objects.all().first()
        created_date = orga.created_at
        created_date = created_date.replace(day=30, month=12, year=2023)
        Organisation.objects.filter(pk=orga.pk).update(created_at=created_date)

        self.maxDiff = None
        self.client.force_login(self.root)

        response = self.client.get(
            reverse("fne_organisations-list"),
            {"created_at__lte": "2024-01-01"},
            format="json",
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": orga.id,
                        "uuid": str(orga.uuid),
                        "url": (
                            "http://testserver"
                            + reverse("fne_organisations-detail", args=(orga.uuid,))
                        ),
                        "is_active": orga.is_active,
                        "name": orga.name,
                        "city": orga.city,
                        "created_at": (
                            f"{orga.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "updated_at": (
                            f"{orga.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "zipcode": orga.zipcode,
                        "siret": orga.siret,
                        "city_insee_code": orga.city_insee_code,
                        "address": orga.address,
                        "address_complement": orga.address_complement,
                        "num_mandats": orga.num_mandats,
                        "france_services_label": orga.france_services_label,
                        "france_services_number": orga.france_services_number,
                    }
                    for orga in Organisation.objects.filter(pk=orga.pk)
                ],
            },
            json.loads(response.content),
        )

    def test_filter_orga_updated_at(self):
        orga = Organisation.objects.all().first()
        created_date = orga.created_at
        created_date = created_date.replace(day=30, month=12, year=2023)
        Organisation.objects.filter(pk=orga.pk).update(
            created_at=created_date, updated_at=created_date
        )

        self.maxDiff = None
        self.client.force_login(self.root)

        response = self.client.get(
            reverse("fne_organisations-list"),
            {"updated_at__lte": "2024-01-01"},
            format="json",
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": orga.id,
                        "uuid": str(orga.uuid),
                        "url": (
                            "http://testserver"
                            + reverse("fne_organisations-detail", args=(orga.uuid,))
                        ),
                        "is_active": orga.is_active,
                        "name": orga.name,
                        "city": orga.city,
                        "created_at": (
                            f"{orga.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "updated_at": (
                            f"{orga.updated_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
                        ),
                        "zipcode": orga.zipcode,
                        "siret": orga.siret,
                        "city_insee_code": orga.city_insee_code,
                        "address": orga.address,
                        "address_complement": orga.address_complement,
                        "num_mandats": orga.num_mandats,
                        "france_services_label": orga.france_services_label,
                        "france_services_number": orga.france_services_number,
                    }
                    for orga in Organisation.objects.filter(pk=orga.pk)
                ],
            },
            json.loads(response.content),
        )
