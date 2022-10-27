from django.test import TestCase

from aidants_connect_habilitation.forms import AidantRequestFormSet
from aidants_connect_habilitation.tests.factories import DraftOrganisationRequestFactory
from aidants_connect_habilitation.tests.utils import get_form


class Test(TestCase):
    def test_get_base_model_form_set(self):
        organisation = DraftOrganisationRequestFactory()
        formset: AidantRequestFormSet = get_form(
            AidantRequestFormSet, form_init_kwargs={"organisation": organisation}
        )
        self.assertEqual(len(formset), 10)
        self.assertTrue(formset.is_valid())

        formset = AidantRequestFormSet(data=formset.data, organisation=organisation)
        self.assertEqual(len(formset), 10)
        self.assertTrue(formset.is_valid())
