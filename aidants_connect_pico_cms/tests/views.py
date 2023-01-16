from django.test import TestCase, tag
from django.test.client import Client

from aidants_connect_pico_cms.tests.factories import TestimonyFactory


@tag("pico_cms")
class TestimonyViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.daphne = TestimonyFactory(name="Daphné Dante", slug="daphne-dante")
        cls.maite = TestimonyFactory(name="Maïté Moignage", slug="maite-moignage")

    def test_right_template_is_used_and_content_is_here(self):
        response = self.client.get("/temoignages/daphne-dante/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_pico_cms/testimony_detail.html"
        )
        self.assertContains(response, "Daphné Dante")
        self.assertContains(response, "Maïté Moignage")

    def test_404_on_nonexisting_testimony(self):
        response = self.client.get("/temoignages/pamela-bsence/")
        self.assertEqual(response.status_code, 404)
