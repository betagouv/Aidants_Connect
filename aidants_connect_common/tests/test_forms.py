from unittest.mock import MagicMock, PropertyMock, patch

from django import forms
from django.core.exceptions import ValidationError
from django.forms.formsets import (
    INITIAL_FORM_COUNT,
    MAX_NUM_FORM_COUNT,
    MIN_NUM_FORM_COUNT,
    TOTAL_FORM_COUNT,
    BaseFormSet,
)
from django.test import TestCase, tag

from dsfr.forms import DsfrDjangoTemplates

from aidants_connect_common.forms import BaseModelMultiForm, BaseMultiForm
from aidants_connect_web.models import Aidant, Organisation
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


class _TestForm(forms.Form):
    test = forms.IntegerField()


_TestFormset = forms.formset_factory(_TestForm)


class _TestMultiForm(BaseMultiForm):
    test = _TestForm
    tests = _TestFormset


_TestModelFormset = forms.modelformset_factory(
    Aidant,
    fields=(
        "id",
        "email",
        "last_name",
        "first_name",
        "profession",
        "phone",
        "organisation",
        "username",
    ),
    extra=0,
)


class _TestModelMultiForm(BaseModelMultiForm):
    test = _TestForm
    tests = _TestModelFormset


@tag("forms")
class TestBaseMultiForm(TestCase):
    def test_instanciate(self):
        form = _TestMultiForm()
        self.assertFalse(form.errors)

    def test_instanciate_with_params(self):
        renderer = DsfrDjangoTemplates()
        form = _TestMultiForm(
            auto_id="id-%s",
            prefix="metaform",
            initial={"test": "test"},
            error_class=None,
            form_kwargs={
                "test": {"prefix": "the_test"},
                "tests": {"prefix": "the_tests"},
            },
            renderer=renderer,
        )
        self.assertFalse(form.errors)
        self.assertEqual("the_test", form["test"].prefix)
        self.assertEqual("the_tests", form["tests"].prefix)
        self.assertEqual(renderer, form["test"].renderer)
        self.assertEqual(renderer, form["tests"].renderer)

    def test_valid(self):
        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): 6,
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): 1,
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): 100,
                form["tests"].forms[0].add_prefix("test"): 12,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            {
                "test": {"test": 6},
                "tests": [{"test": 12}],
            },
            form.cleaned_data,
        )

    def test_invalid(self):
        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): "NaN",
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): object(),
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): object(),
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): object(),
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): object(),
                form["tests"].forms[0].add_prefix("test"): "NaN",
            }
        )
        form.is_valid()
        self.assertFalse(form.is_valid())
        self.assertEqual(
            {
                "__all__": {
                    "tests": [
                        "Des données du formulaire ManagementForm sont manquantes ou "
                        "ont été manipulées. Champs manquants : "
                        "multiform-tests-TOTAL_FORMS, "
                        "multiform-tests-INITIAL_FORMS, "
                        "multiform-tests-MIN_NUM_FORMS, "
                        "multiform-tests-MAX_NUM_FORMS. "
                        "Vous pourriez créer un rapport de "
                        "bogue si le problème persiste."
                    ]
                },
                "test": {"test": ["Saisissez un nombre entier."]},
            },
            form.errors,
        )
        self.assertRaises(AttributeError, getattr, form, "cleaned_data")

        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): "NaN",
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): 1,
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): 0,
                form["tests"].forms[0].add_prefix("test"): "NaN",
            }
        )
        form.is_valid()
        self.assertFalse(form.is_valid())
        self.assertEqual(
            {
                "test": {"test": ["Saisissez un nombre entier."]},
                "tests": [{"test": ["Saisissez un nombre entier."]}],
            },
            form.errors,
        )
        self.assertRaises(AttributeError, getattr, form, "cleaned_data")

        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): 6,
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): 1,
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): 0,
                form["tests"].forms[0].add_prefix("test"): "NaN",
            }
        )
        form.is_valid()
        self.assertFalse(form.is_valid())
        self.assertEqual(
            {"tests": [{"test": ["Saisissez un nombre entier."]}]},
            form.errors,
        )
        self.assertEqual({"test": {"test": 6}}, form.cleaned_data)

    def test_clean_raises_validation_error(self):
        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): 6,
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): 1,
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): 0,
                form["tests"].forms[0].add_prefix("test"): "NaN",
            }
        )

        form.clean = MagicMock(side_effect=ValidationError("Woops"))
        self.assertEqual(
            {
                "__all__": {"__all__": ["Woops"]},
                "tests": [{"test": ["Saisissez un nombre entier."]}],
            },
            form.errors,
        )

    def test_add_non_field_error(self):
        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): 6,
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): 1,
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): 0,
                form["tests"].forms[0].add_prefix("test"): 12,
            }
        )

        self.assertTrue(form.is_valid())

        form.add_non_field_error(None, "1")
        form.add_non_field_error(None, ValidationError("2"))
        form.add_non_field_error("test", "1")
        form.add_non_field_error("test", ValidationError("2"))
        form.add_non_field_error("tests", "1")
        form.add_non_field_error("tests", ValidationError("2"))
        self.assertRaises(
            ValueError, form.add_non_field_error, "non_existant_form", "1"
        )
        self.assertRaises(
            ValueError,
            form.add_non_field_error,
            "non_existant_form",
            ValidationError("2"),
        )
        self.assertEqual(
            {
                "__all__": {"__all__": ["1", "2"], "tests": ["1", "2"]},
                "test": {"__all__": ["1", "2"]},
            },
            form.errors,
        )

    def test_repr(self):
        self.assertEqual(
            "<_TestMultiForm bound=False, valid=Unknown, "
            f"form_classes={{'test': {_TestForm}, 'tests': {_TestFormset}}}>",
            str(_TestMultiForm()),
        )
        form = _TestMultiForm()
        form = _TestMultiForm(
            {
                form["test"].add_prefix("test"): 6,
                form["tests"].management_form.add_prefix(TOTAL_FORM_COUNT): 1,
                form["tests"].management_form.add_prefix(INITIAL_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MIN_NUM_FORM_COUNT): 0,
                form["tests"].management_form.add_prefix(MAX_NUM_FORM_COUNT): 100,
                form["tests"].forms[0].add_prefix("test"): 12,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            "<_TestMultiForm bound=True, valid=True, "
            f"form_classes={{'test': {_TestForm}, 'tests': {_TestFormset}}}>",
            str(form),
        )

    def test_extend(self):
        class _TestMultiForm2(_TestMultiForm):
            test2 = _TestForm

        form = _TestMultiForm2()
        self.assertEqual({"test", "tests", "test2"}, set(form.forms.keys()))
        self.assertIsInstance(form["test"], _TestForm)
        self.assertIsInstance(form["tests"], BaseFormSet)
        self.assertIsInstance(form["test2"], _TestForm)


@tag("forms")
class TestBaseModelMultiForm(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org1: Organisation = OrganisationFactory()
        cls.aidants1: list[Aidant] = [
            AidantFactory(organisation=cls.org1) for _ in range(3)
        ]
        cls.org2: Organisation = OrganisationFactory()
        cls.aidants2: list[Aidant] = [
            AidantFactory(organisation=cls.org2) for _ in range(3)
        ]

    def test_instanciate_with_params(self):
        renderer = DsfrDjangoTemplates()
        form = _TestModelMultiForm(
            auto_id="id-%s",
            prefix="metaform",
            initial={"test": "test"},
            error_class=None,
            form_kwargs={
                # Testing 'queryset argument is not passed to BaseForm or BaseFormSet
                "test": {"prefix": "the_test"},
                "tests": {"prefix": "the_tests"},
            },
            querysets={"test": Aidant.objects.none(), "tests": self.org1.aidants},
            renderer=renderer,
        )
        self.assertFalse(form.errors)
        self.assertEqual("the_test", form["test"].prefix)
        self.assertEqual("the_tests", form["tests"].prefix)
        self.assertEqual(renderer, form["test"].renderer)
        self.assertEqual(renderer, form["tests"].renderer)

    def test_queryset(self):
        form = _TestModelMultiForm(
            querysets={"test": Aidant.objects.none(), "tests": self.org1.aidants.all()}
        )
        self.assertEqual(3, len(form["tests"].forms))
        self.assertEqual(self.aidants1[0], form["tests"].forms[0].instance)
        self.assertEqual(self.aidants1[1], form["tests"].forms[1].instance)
        self.assertEqual(self.aidants1[2], form["tests"].forms[2].instance)

    def test_save(self):
        names = ["e", "j", "v"]
        additionnal_aidant = AidantFactory.build()
        data = {
            "multiform-test-test": 6,
            "multiform-tests-TOTAL_FORMS": 4,
            "multiform-tests-INITIAL_FORMS": 3,
            "multiform-tests-MIN_NUM_FORMS": 0,
            "multiform-tests-MAX_NUM_FORMS": 1000,
            "multiform-tests-0-id": self.aidants1[0].pk,
            "multiform-tests-0-username": self.aidants1[0].username,
            "multiform-tests-0-first_name": self.aidants1[0].first_name,
            "multiform-tests-0-last_name": names[0],
            "multiform-tests-0-email": self.aidants1[0].email,
            "multiform-tests-0-profession": self.aidants1[0].profession,
            "multiform-tests-0-phone": f"{self.aidants1[0].phone}",
            "multiform-tests-0-organisation": self.org1.pk,
            "multiform-tests-1-id": self.aidants1[1].pk,
            "multiform-tests-1-username": self.aidants1[1].username,
            "multiform-tests-1-first_name": self.aidants1[1].first_name,
            "multiform-tests-1-last_name": names[1],
            "multiform-tests-1-email": self.aidants1[1].email,
            "multiform-tests-1-profession": self.aidants1[1].profession,
            "multiform-tests-1-phone": f"{self.aidants1[1].phone}",
            "multiform-tests-1-organisation": self.org1.pk,
            "multiform-tests-2-id": self.aidants1[2].pk,
            "multiform-tests-2-username": self.aidants1[2].username,
            "multiform-tests-2-first_name": self.aidants1[2].first_name,
            "multiform-tests-2-last_name": names[2],
            "multiform-tests-2-email": self.aidants1[2].email,
            "multiform-tests-2-profession": self.aidants1[2].profession,
            "multiform-tests-2-phone": f"{self.aidants1[2].phone}",
            "multiform-tests-2-organisation": self.org1.pk,
            "multiform-tests-3-id": None,
            "multiform-tests-3-username": additionnal_aidant.username,
            "multiform-tests-3-first_name": additionnal_aidant.first_name,
            "multiform-tests-3-last_name": additionnal_aidant.last_name,
            "multiform-tests-3-email": additionnal_aidant.email,
            "multiform-tests-3-profession": additionnal_aidant.profession,
            "multiform-tests-3-phone": f"{additionnal_aidant.phone}",
            "multiform-tests-3-organisation": self.org1.pk,
        }

        form = _TestModelMultiForm(
            data,
            querysets={"test": Aidant.objects.none(), "tests": self.org1.aidants.all()},
        )
        self.assertEqual(3, len(self.org1.aidants.all()))

        form.save()

        self.org1.refresh_from_db()
        self.assertEqual(4, len(self.org1.aidants.all()))
        self.assertEqual(
            {*names, additionnal_aidant.last_name},
            set(self.org1.aidants.all().values_list("last_name", flat=True)),
        )
        added_aidant = self.org1.aidants.last()
        self.assertEqual(
            {
                "id": added_aidant.pk,  # not important
                "username": additionnal_aidant.username,
                "first_name": additionnal_aidant.first_name,
                "last_name": additionnal_aidant.last_name,
                "email": additionnal_aidant.email,
                "profession": additionnal_aidant.profession,
                "phone": f"{additionnal_aidant.phone}",
                "organisation": self.org1,
            },
            {k: getattr(added_aidant, k) for k in form["tests"].forms[0].fields.keys()},
        )

        # Test raising error
        with patch(
            "aidants_connect_common.tests.test_forms._TestModelMultiForm.errors",
            new_callable=PropertyMock,
        ) as mock_errors:
            mock_errors.return_value = {"test": ValidationError("Woops!")}
            form = _TestModelMultiForm(
                data,
                querysets={
                    "test": Aidant.objects.none(),
                    "tests": self.org1.aidants.all(),
                },
            )
            self.assertRaises(ValueError, form.save)
