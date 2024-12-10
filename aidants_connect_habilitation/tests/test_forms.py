from unittest.mock import Mock, patch
from urllib.parse import quote, unquote

from django.conf import settings
from django.test import TestCase, override_settings

from aidants_connect_common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_common.utils.gouv_address_api import Address
from aidants_connect_habilitation.forms import (
    AddressValidatableMixin,
    AidantRequestFormLegacy,
    AidantRequestFormSet,
    IssuerForm,
    ManagerForm,
    OrganisationRequestForm,
    ValidationForm,
)
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    DraftOrganisationRequestFactory,
    ManagerFactory,
    OrganisationRequestFactory,
    address_factory,
)
from aidants_connect_habilitation.tests.utils import get_form
from aidants_connect_web.models import OrganisationType


class TestIssuerForm(TestCase):
    def test_form_is_valid_with_dom_tom_phonenumber(self):
        form = IssuerForm(
            data={
                "phone": "06 90 11 12 13",
                "first_name": "Mary",
                "last_name": "Read",
                "profession": "Pirate",
                "email": "mary_read@example.com",
            }
        )

        self.assertTrue(form.is_valid())

    def test_email_lower(self):
        form = get_form(
            IssuerForm,
            email="TEST@TEST.TEST",
        )

        self.assertTrue(form.is_valid())
        self.assertEqual("test@test.test", form.cleaned_data["email"])


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
                "Ce champ doit être rempli si la structure est de type "
                f"{RequestOriginConstants.OTHER.label}."
            ],
        )

    def test_clean_type_zipcode_number_passes(self):
        form = get_form(
            OrganisationRequestForm,
            ignore_errors=True,
            type_id=RequestOriginConstants.OTHER.value,
            zipcode="01700",
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})

    def test_clean_type_zipcode_not_number_raises_error(self):
        form = get_form(
            OrganisationRequestForm,
            ignore_errors=True,
            type_id=RequestOriginConstants.OTHER.value,
            zipcode="La Commune",
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["zipcode"], ["Veuillez entrer un code postal valide"]
        )

    def test_france_services_label_requires_fs_number(self):
        form = get_form(
            OrganisationRequestForm,
            france_services_label=True,
            france_services_number=None,
            ignore_errors=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "merci de renseigner son numéro", form.errors["france_services_number"][0]
        )

    def test_france_services_label_keeps_fs_number(self):
        form = get_form(
            OrganisationRequestForm,
            france_services_label=True,
            france_services_number=444666999,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["france_services_number"], 444666999)

    def test_no_france_services_label_clears_fs_number(self):
        form = get_form(
            OrganisationRequestForm,
            france_services_label=False,
            france_services_number=444666999,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual("", form.cleaned_data["france_services_number"])


class TestValidationFormForm(TestCase):
    names_attr = ["cgu", "not_free", "dpo", "professionals_only", "without_elected"]

    def test_form_valid_only_with_four_enabled_choices(self):
        form = ValidationForm()
        self.assertFalse(form.is_valid())

        form = ValidationForm(data={"cgu": True})
        self.assertFalse(form.is_valid())

        form = ValidationForm(
            data={name: True for name in TestValidationFormForm.names_attr}
        )
        self.assertTrue(form.is_valid())

    def test_form_valid_works(self):
        orga_request = DraftOrganisationRequestFactory(
            cgu=False,
            not_free=False,
            dpo=False,
            professionals_only=False,
            without_elected=False,
            manager=ManagerFactory(),
        )

        form = ValidationForm(
            data={name: True for name in TestValidationFormForm.names_attr}
        )
        form.is_valid()

        orga = form.save(organisation=orga_request)
        self.assertEqual(
            orga.status, RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        for name in TestValidationFormForm.names_attr:
            with self.subTest(f"{name} field validated"):
                self.assertTrue(getattr(orga, name))


class TestManagerForm(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationRequestFactory()

    def test_clean_type_zipcode_number_passes(self):
        form = get_form(
            ManagerForm,
            ignore_errors=True,
            zipcode="01700",
            form_init_kwargs={"organisation": self.organisation},
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})

    def test_clean_type_zipcode_not_number_raises_error(self):
        form = get_form(
            ManagerForm,
            ignore_errors=True,
            zipcode="La Commune",
            form_init_kwargs={"organisation": self.organisation},
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["zipcode"], ["Veuillez entrer un code postal valide"]
        )

    def test_email_lower(self):
        form = get_form(
            ManagerForm,
            email="TEST@TEST.TEST",
            form_init_kwargs={"organisation": self.organisation},
        )

        self.assertTrue(form.is_valid())
        self.assertEqual("test@test.test", form.cleaned_data["email"])

    def test_email_conseiller_numerique(self):
        form = get_form(
            ManagerForm,
            ignore_errors=True,
            conseiller_numerique=True,
            email="test@test.test",
            form_init_kwargs={"organisation": self.organisation},
        )

        self.assertTrue(form.is_valid())


class TestAidantRequestForm(TestCase):
    def test_clean_aidant_with_same_email_as_manager(self):
        # Case manager is aidant: error
        manager = ManagerFactory(is_aidant=True)
        organisation = OrganisationRequestFactory(manager=manager)
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            email=organisation.manager.email,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            [
                "Le ou la référente de cette organisation est aussi déclarée"
                f"comme aidante avec l'email '{organisation.manager.email}'. "
                "Chaque aidant ou aidante doit avoir son propre e-mail nominatif."
            ],
            form.errors["email"],
        )

        # Case manager is not aidant: no error
        manager = ManagerFactory(is_aidant=False)
        organisation = OrganisationRequestFactory(manager=manager)
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            email=organisation.manager.email,
        )

        self.assertTrue(form.is_valid())

    def test_clean_aidant_with_same_email_as_another_aidant(self):
        organisation = OrganisationRequestFactory()
        aidant = AidantRequestFactory(organisation=organisation)
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            email=aidant.email,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            [
                f"Il y a déjà un aidant ou une aidante avec l'adresse email "
                f"'{aidant.email}' dans cette organisation. Chaque aidant ou "
                f"aidante doit avoir son propre e-mail nominatif."
            ],
            form.errors["email"],
        )

    def test_clean_aidant_modifying_email_of_an_existing_user(self):
        organisation = OrganisationRequestFactory()
        aidant = AidantRequestFactory(organisation=organisation)
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation, "instance": aidant},
            email="test@test.test",
        )

        self.assertTrue(form.is_valid())

    def test_clean_aidant_modifying_email_of_an_existing_user_with_already_existing_user(  # noqa
        self,
    ):
        organisation = OrganisationRequestFactory()
        aidant1 = AidantRequestFactory(organisation=organisation)
        aidant2 = AidantRequestFactory(organisation=organisation)
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation, "instance": aidant1},
            email=aidant2.email,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            [
                f"Il y a déjà un aidant ou une aidante avec l'adresse email "
                f"'{aidant2.email}' dans cette organisation. Chaque aidant ou "
                f"aidante doit avoir son propre e-mail nominatif."
            ],
            form.errors["email"],
        )

    def test_email_conseiller_numerique(self):
        organisation = OrganisationRequestFactory()
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            conseiller_numerique=True,
            email="test@test.test",
        )

        self.assertTrue(form.is_valid())
        # self.assertEqual(
        #     form.errors["email"][0],
        #     "Si la personne fait partie du dispositif conseiller numérique, "
        #     "elle doit s'inscrire avec son email "
        #     f"{settings.CONSEILLER_NUMERIQUE_EMAIL}",
        # )

    def test_email_conseiller_numerique_with_deprecated_email(self):
        organisation = OrganisationRequestFactory()
        form = get_form(
            AidantRequestFormLegacy,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            conseiller_numerique=True,
            email="test@conseiller-numerique.fr",
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["email"][0],
            "Suite à l'annonce de l'arrêt des adresses emails "
            f"{settings.CONSEILLER_NUMERIQUE_EMAIL}"
            " le 15 novembre 2024, nous vous invitons à renseigner"
            " une autre adresse email nominative et professionnelle.",
        )


class TestBaseAidantRequestFormSet(TestCase):
    def test_is_empty(self):
        organisation = DraftOrganisationRequestFactory()
        form: AidantRequestFormSet = get_form(
            AidantRequestFormSet,
            form_init_kwargs={"initial": 0, "organisation": organisation},
            ignore_errors=True,
        )
        self.assertEqual(form.is_empty(), True)

        form: AidantRequestFormSet = get_form(
            AidantRequestFormSet,
            form_init_kwargs={"organisation": organisation},
            ignore_errors=True,
        )
        self.assertEqual(form.is_empty(), False)

        # Correctly handle erroneous subform case
        data = get_form(
            AidantRequestFormSet,
            form_init_kwargs={"initial": 1, "organisation": organisation},
        ).data
        data["form-0-email"] = "   "
        form = AidantRequestFormSet(data=data, organisation=organisation)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.is_empty(), False)

    def test_clean_multiple_aidants_with_same_email(self):
        organisation = DraftOrganisationRequestFactory()
        form = get_form(
            AidantRequestFormSet,
            ignore_errors=True,
            form_init_kwargs={"initial": 2, "organisation": organisation},
            email="karl_marx@internationale.de",
        )

        self.assertFalse(form.is_valid())
        error_message = (
            "Il y a déjà un aidant ou une aidante avec l'adresse email "
            "'karl_marx@internationale.de' dans cette organisation. "
            "Chaque aidant ou aidante doit avoir son propre e-mail nominatif."
        )
        self.assertEqual(
            [[error_message], [error_message]],
            [subform.errors["email"] for subform in form.forms],
        )


@override_settings(GOUV_ADDRESS_SEARCH_API_DISABLED=False)
class TestAddressValidatableMixin(TestCase):
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_alternative_address_becomes_required_after_submission_with_multiple_results(  # noqa
        self, search_adresses_mock: Mock
    ):
        class TestForm(AddressValidatableMixin):
            def get_address_for_search(self) -> str:
                return ""

            def autocomplete(self, address: Address):
                pass

        # First submission: address API returns empty result
        search_adresses_mock.return_value = []
        form = TestForm(data={})

        self.assertFalse(form.fields["alternative_address"].required)
        self.assertFalse(form.fields["alternative_address"].widget.is_required)

        form.is_valid()

        self.assertFalse(form.fields["alternative_address"].required)
        self.assertFalse(form.fields["alternative_address"].widget.is_required)

        # Second submission: address API returns 1 result
        search_adresses_mock.reset_mock()
        search_adresses_mock.return_value = [address_factory()]
        form = TestForm(data={})

        self.assertFalse(form.fields["alternative_address"].required)
        self.assertFalse(form.fields["alternative_address"].widget.is_required)

        form.is_valid()

        self.assertTrue(form.fields["alternative_address"].required)
        self.assertTrue(form.fields["alternative_address"].widget.is_required)

    @patch("aidants_connect_habilitation.forms.AddressValidatableMixin.autocomplete")
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_I_can_autocomplete_with_one_of_the_propositions(
        self, _, autocomplete_mock: Mock
    ):
        cached_api_result = quote(address_factory().json())

        form = AddressValidatableMixin(data={"alternative_address": cached_api_result})

        address = Address.parse_raw(unquote(cached_api_result))

        # Simulate POSTing data
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["alternative_address"], address)

        # Simulate autocompleting: AddressValidatableMixin.post_clean
        # must be called in derived form's clean function
        form.post_clean()
        self.assertNotIn("alternative_address", form.cleaned_data)
        autocomplete_mock.assert_called_with(address)

        autocomplete_mock.reset_mock()

    @patch(
        "aidants_connect_habilitation.forms.AddressValidatableMixin.get_address_for_search"  # noqa
    )
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_form_leaves_me_alone_if_API_id_down(
        self, search_adresses_mock: Mock, get_address_for_search: Mock
    ):
        address = address_factory()
        search_address = f"{address.name} {address.postcode} {address.city}"
        get_address_for_search.return_value = search_address
        search_adresses_mock.return_value = []

        form = AddressValidatableMixin(data={})

        # Simulate POST
        self.assertTrue(form.is_valid())
        search_adresses_mock.assert_called_with(search_address)
        self.assertEqual(
            form.cleaned_data["alternative_address"],
            AddressValidatableMixin.DEFAULT_CHOICE,
        )

        # Simulate autocompleting: AddressValidatableMixin.post_clean
        # must be called in derived form's clean function
        form.post_clean()
        self.assertNotIn("alternative_address", form.cleaned_data)

    @patch("aidants_connect_habilitation.forms.AddressValidatableMixin.autocomplete")
    @patch(
        "aidants_connect_habilitation.forms.AddressValidatableMixin.get_address_for_search"  # noqa
    )
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_form_leaves_me_alone_if_I_entered_a_correct_address(
        self,
        search_adresses_mock: Mock,
        get_address_for_search: Mock,
        autocomplete_mock: Mock,
    ):
        address = address_factory(score=0.95)
        search_address = f"{address.name} {address.postcode} {address.city}"
        get_address_for_search.return_value = search_address
        search_adresses_mock.return_value = [address]

        form = AddressValidatableMixin(data={})

        # Simulate POST
        self.assertTrue(form.is_valid())
        search_adresses_mock.assert_called_with(search_address)
        self.assertEqual(form.cleaned_data["alternative_address"], address)

        # Simulate autocompleting: AddressValidatableMixin.post_clean
        # must be called in derived form's clean function
        form.post_clean()
        self.assertNotIn("alternative_address", form.cleaned_data)
        autocomplete_mock.assert_called_with(address)

    @patch(
        "aidants_connect_habilitation.forms.AddressValidatableMixin.get_address_for_search"  # noqa
    )
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_form_raises_validation_error_on_multiple_results(
        self, search_adresses_mock: Mock, get_address_for_search: Mock
    ):
        addresses = [address_factory(score=0.95) for _ in range(3)]
        get_address_for_search.return_value = "3, rue de la Marne 95000 Rennes"
        search_adresses_mock.return_value = addresses

        form = AddressValidatableMixin(data={})

        # Simulate POST
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {"alternative_address": ["Plusieurs choix d'adresse sont possibles"]},
        )

    @patch("aidants_connect_habilitation.forms.AddressValidatableMixin.autocomplete")
    @patch(
        "aidants_connect_habilitation.forms.AddressValidatableMixin.get_address_for_search"  # noqa
    )
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_disable_backend_validation(
        self,
        search_adresses_mock: Mock,
        get_address_for_search: Mock,
        autocomplete_mock: Mock,
    ):
        form = AddressValidatableMixin(data={"skip_backend_validation": True})

        # Simulate POST
        self.assertTrue(form.is_valid())

        search_adresses_mock.assert_not_called()
        get_address_for_search.assert_not_called()
        autocomplete_mock.assert_not_called()
