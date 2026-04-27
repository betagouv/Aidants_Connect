from django.test import TestCase, tag
from django.urls import reverse


@tag("habiliation")
class HabilitationPageTests(TestCase):

    def test_habilitation_has_good_faq_link(self):
        response = self.client.get(reverse("habilitation_faq_habilitation"))
        self.assertTemplateUsed(response, "public_website/habilitation.html")
        self.assertContains(response, "faq_public")
        self.assertNotContains(response, "faq/lhabilitation-aidants-connect")
