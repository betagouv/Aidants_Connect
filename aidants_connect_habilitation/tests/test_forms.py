from django.test import TestCase

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_habilitation.forms import OrganisationRequestForm
from aidants_connect_habilitation.tests.utils import get_form
from aidants_connect_web.models import OrganisationType


class TestOrganisationRequestForm(TestCase):
    def test_clean_type_passes(self):
        form = get_form(
            OrganisationRequestForm,
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["type"],
            OrganisationType.objects.get(pk=RequestOriginConstants.MEDIATHEQUE.value),
        )

    def test_clean_type_other_returns_user_value(self):
        form = get_form(
            OrganisationRequestForm,
            type_id=RequestOriginConstants.OTHER.value,
            type_other="L'organisation des travaillleurs",
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["type_other"], "L'organisation des travaillleurs"
        )

    def test_clean_type_other_returns_blank_on_specific_org_type(self):
        form = get_form(
            OrganisationRequestForm,
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
            type_other="L'organisation des travaillleurs",
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["type_other"], "")

    def test_clean_type_other_unspecified_raises_error(self):
        form = get_form(
            OrganisationRequestForm,
            ignore_errors=True,
            type_id=RequestOriginConstants.OTHER.value,
            type_other=None,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["type_other"],
            [
                f"Le champ « Type de structure si autre » doit être rempli "
                f"si la structure est de type {RequestOriginConstants.OTHER.label}."
            ],
        )
