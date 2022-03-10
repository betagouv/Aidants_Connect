from unittest.mock import Mock, patch

from django.test import TestCase

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    DataPrivacyOfficerForm,
    ManagerForm,
    OrganisationRequestForm,
    PersonnelForm,
)
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import DraftOrganisationRequestFactory
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


class TestPersonnelForm(TestCase):
    @patch("aidants_connect_habilitation.forms.ManagerForm.is_valid")
    @patch("aidants_connect_habilitation.forms.DataPrivacyOfficerForm.is_valid")
    @patch("aidants_connect_habilitation.forms.AidantRequestFormSet.is_valid")
    def test_is_valid(
        self,
        mock_manager_form_is_valid: Mock,
        mock_dpo_form_is_valid: Mock,
        mock_aidants_form_is_valid: Mock,
    ):
        form = PersonnelForm()

        mock_manager_form_is_valid.return_value = True
        mock_dpo_form_is_valid.return_value = True
        mock_aidants_form_is_valid.return_value = True

        self.assertTrue(form.is_valid())

        mock_manager_form_is_valid.return_value = False
        mock_dpo_form_is_valid.return_value = True
        mock_aidants_form_is_valid.return_value = True

        self.assertFalse(form.is_valid())

        mock_manager_form_is_valid.return_value = True
        mock_dpo_form_is_valid.return_value = False
        mock_aidants_form_is_valid.return_value = True

        self.assertFalse(form.is_valid())

        mock_manager_form_is_valid.return_value = True
        mock_dpo_form_is_valid.return_value = True
        mock_aidants_form_is_valid.return_value = False

        self.assertFalse(form.is_valid())

    def test_save(self):
        organisation: OrganisationRequest = DraftOrganisationRequestFactory()

        manager_data = get_form(ManagerForm).clean()
        dpo_data = get_form(DataPrivacyOfficerForm).clean()
        aidants_form = get_form(AidantRequestFormSet)
        aidants_data = aidants_form.data

        cleaned_data = {
            **{
                f"{PersonnelForm.MANAGER_FORM_PREFIX}-{k}": v
                for k, v in manager_data.items()
            },
            **{f"{PersonnelForm.DPO_FORM_PREFIX}-{k}": v for k, v in dpo_data.items()},
            **{
                k.replace("form-", f"{PersonnelForm.AIDANTS_FORMSET_PREFIX}-"): v
                for k, v in aidants_data.items()
            },
        }

        form = PersonnelForm(data=cleaned_data)
        self.assertTrue(form.is_valid())

        self.assertIs(organisation.data_privacy_officer, None)
        self.assertIs(organisation.manager, None)
        self.assertEqual(organisation.aidant_requests.count(), 0)

        form.save(organisation)

        self.assertEqual(organisation.data_privacy_officer.email, dpo_data["email"])
        self.assertEqual(organisation.manager.email, manager_data["email"])
        self.assertEqual(organisation.aidant_requests.count(), len(aidants_form.forms))
        self.assertNotEqual(organisation.aidant_requests.count(), 0)
