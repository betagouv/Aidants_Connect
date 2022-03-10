from django.test import TestCase

from aidants_connect_habilitation.forms import AidantRequestFormSet
from aidants_connect_habilitation.tests.utils import get_form


class Test(TestCase):
    def test_get_base_model_form_set(self):
        formset: AidantRequestFormSet = get_form(AidantRequestFormSet)
        self.assertEqual(len(formset), 10)
        self.assertTrue(formset.is_valid())

        formset = AidantRequestFormSet(data=formset.data)
        self.assertEqual(len(formset), 10)
        self.assertTrue(formset.is_valid())
