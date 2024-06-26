from django.test import TestCase, tag
from django.test.client import Client

from aidants_connect_pico_cms.models import FaqCategory
from aidants_connect_pico_cms.tests.factories import (  # FaqQuestionFactory,
    FaqCategoryFactory,
    TestimonyFactory,
)
from aidants_connect_web.tests.factories import AidantFactory


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


@tag("pico_cms", "faq")
class TestFaqViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.faq_section_2 = FaqCategoryFactory(
            name="Deuxième section de FAQ", slug="seconde-section", sort_order=20
        )
        cls.faq_section_1 = FaqCategoryFactory(
            name="Première section de FAQ", slug="premiere-section", sort_order=10
        )

        cls.aidant_1 = AidantFactory(is_staff=True)
        cls.aidant_2 = AidantFactory(is_staff=False)

    def test_right_template_is_used_and_content_is_here(self):
        response = self.client.get(self.faq_section_1.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_pico_cms/faqcategory_detail.html"
        )
        self.assertContains(response, "Première section de FAQ")
        self.assertContains(response, "Deuxième section de FAQ")

    def test_default_faq_route_renders_the_first_published_section(self):
        response = self.client.get("/faq/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_pico_cms/faqcategory_detail.html"
        )
        self.assertContains(response, "Première section de FAQ")
        self.assertContains(response, "Deuxième section de FAQ")
        self.assertEqual(self.faq_section_1, response.context["object"])

    def test_404_if_no_section_is_published(self):
        FaqCategory.objects.update(published=False)
        response = self.client.get("/faq/")
        self.assertEqual(response.status_code, 404)

    def test_renders_unpublished_if_user_is_authorized(self):
        FaqCategory.objects.update(published=False)
        self.client.force_login(self.aidant_1)
        response = self.client.get(f"{self.faq_section_1.get_absolute_url()}?see_draft")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_pico_cms/faqcategory_detail.html"
        )
        self.assertContains(response, "Première section de FAQ")
        self.assertContains(response, "Deuxième section de FAQ")
        self.client.force_login(self.aidant_2)
        response = self.client.get(f"{self.faq_section_1.get_absolute_url()}?see_draft")
        self.assertEqual(response.status_code, 404)
