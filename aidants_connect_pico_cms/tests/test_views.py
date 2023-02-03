from django.conf import settings
from django.test import TestCase, override_settings, tag
from django.test.client import Client

from aidants_connect_pico_cms.tests.factories import (  # FaqQuestionFactory,
    FaqCategoryFactory,
    TestimonyFactory,
)


@tag("pico_cms")
class TestTestimonyViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.daphne = TestimonyFactory(
            name="Daphné Dante", slug="daphne-dante", published=True
        )
        cls.maite = TestimonyFactory(
            name="Maïté Moignage", slug="maite-moignage", published=True
        )
        cls.cachee = TestimonyFactory(
            name="Malika Chée", slug="malika", published=False
        )

    def test_right_template_is_used_and_content_is_here(self):
        response = self.client.get("/temoignages/daphne-dante/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_pico_cms/testimony_detail.html"
        )
        self.assertContains(response, "Daphné Dante")
        self.assertContains(response, "Maïté Moignage")
        self.assertNotContains(response, "Malika Chée")

    def test_404_on_nonexisting_testimony(self):
        response = self.client.get("/temoignages/pamela-bsence/")
        self.assertEqual(response.status_code, 404)


@tag("pico_cms")
@override_settings(FF_USE_PICO_CMS_FOR_FAQ=True)
class TestFaqViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.faq_section_1 = FaqCategoryFactory(
            name="Première section de FAQ", slug="premiere-section", sort_order=10
        )
        cls.faq_section_2 = FaqCategoryFactory(
            name="Deuxième section de FAQ", slug="seconde-section", sort_order=20
        )

    def test_right_template_is_used_and_content_is_here(self):
        self.assertTrue(settings.FF_USE_PICO_CMS_FOR_FAQ)
        response = self.client.get(self.faq_section_1.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_pico_cms/faqcategory_detail.html"
        )
        self.assertContains(response, "Première section de FAQ")
        self.assertContains(response, "Deuxième section de FAQ")
