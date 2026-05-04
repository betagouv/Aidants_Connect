"""Permanent redirects from historical URL prefixes."""

from django.test import TestCase
from django.urls import reverse


class LegacyEspaceResponsableRedirectTests(TestCase):
    def test_root_redirects_to_espace_referent(self):
        response = self.client.get("/espace-responsable/", follow=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], reverse("espace_referent:home"))

    def test_subpath_redirects_preserving_suffix(self):
        response = self.client.get("/espace-responsable/organisation/", follow=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], reverse("espace_referent:organisation"))

    def test_aidant_detail_redirects(self):
        response = self.client.get("/espace-responsable/aidant/42/", follow=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response["Location"],
            reverse("espace_referent:aidant_detail", kwargs={"aidant_id": 42}),
        )


class LegacyEspaceAidantRootRedirectTests(TestCase):
    def test_usagers_redirects(self):
        response = self.client.get("/usagers/", follow=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], reverse("espace_aidant:usagers"))

    def test_creation_mandat_redirects(self):
        response = self.client.get("/creation_mandat/", follow=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], reverse("espace_aidant:new_mandat"))
