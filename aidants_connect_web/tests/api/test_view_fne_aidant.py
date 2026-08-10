import json

from django.urls import reverse

from rest_framework.test import APITestCase

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


class FNEAidantViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga_inactive = OrganisationFactory(name="INACTIVE ORGA", is_active=False)
        cls.orga = OrganisationFactory(name="ORGANISATION")
        cls.orga_user = OrganisationFactory(name="ORGA USER")
        cls.orga_aidant = OrganisationFactory(name="ORGANISATION AIDANT")

        cls.root = AidantFactory(
            username="root@root.fr",
            organisation=cls.orga_user,
            is_active=True,
            is_staff=True,
        )
        cls.aidant = AidantFactory(
            username="aidant@aidant.fr",
            organisation=cls.orga_aidant,
            is_active=True,
            is_staff=False,
            email="aidant@aidant.fr",
            can_create_mandats=True,
        )
        cls.aidant_two = AidantFactory(
            username="aidant2@aidant.fr",
            email="aidant2@aidant.fr",
            organisation=cls.orga_aidant,
            is_active=True,
            is_staff=False,
            can_create_mandats=True,
        )

    def test_list_post_disallowed(self):
        self.client.force_login(self.root)
        response = self.client.post(reverse("fne_aidants-list"), {}, format="json")
        self.assertEqual(405, response.status_code)
        self.assertDictEqual(
            {"detail": "Méthode « POST » non autorisée."},
            json.loads(response.content),
        )

    def test_list_get_paginated(self):
        self.maxDiff = None
        self.client.force_login(self.root)

        response = self.client.get(reverse("fne_aidants-list"), {}, format="json")
        d_response = json.loads(response.content)

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, d_response["count"])

    def test_detail_post_disallowed(self):
        self.client.force_login(self.root)
        response = self.client.post(
            reverse("fne_aidants-detail", args=(self.aidant.id,)),
            {},
            format="json",
        )
        self.assertEqual(405, response.status_code)
        self.assertDictEqual(
            {"detail": "Méthode « POST » non autorisée."},
            json.loads(response.content),
        )
