from django.conf import settings
from django.test import TestCase

from aidants_connect_common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_habilitation.forms import (
    AidantRequestForm,
    AidantRequestFormSet,
    IssuerForm,
    OrganisationRequestForm,
    ReferentForm,
    ValidationForm,
)
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    DraftOrganisationRequestFactory,
    ManagerFactory,
    OrganisationRequestFactory,
)
from aidants_connect_habilitation.tests.utils import get_form
from aidants_connect_web.models import HabilitationRequest, OrganisationType
from aidants_connect_web.tests.factories import OrganisationFactory


class TestIssuerForm(TestCase):
    def test_form_is_valid_with_dom_tom_phonenumber(self):
        form = IssuerForm(
            data={
                # "phone": "06 90 11 12 13",
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


class TestValidationForm(TestCase):
    names_attr = ["cgu", "not_free", "dpo", "professionals_only", "without_elected"]

    def test_form_valid_only_with_four_enabled_choices(self):
        form = ValidationForm()
        self.assertFalse(form.is_valid())

        form = ValidationForm(data={"cgu": True})
        self.assertFalse(form.is_valid())

        form = ValidationForm(
            data={name: True for name in TestValidationForm.names_attr}
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
            data={name: True for name in TestValidationForm.names_attr}
        )
        form.is_valid()

        orga = form.save(organisation=orga_request)
        self.assertEqual(
            orga.status, RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        for name in TestValidationForm.names_attr:
            with self.subTest(f"{name} field validated"):
                self.assertTrue(getattr(orga, name))


class TestManagerForm(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationRequestFactory()

    def test_email_lower(self):
        form = get_form(
            ReferentForm,
            email="TEST@TEST.TEST",
            form_init_kwargs={"organisation": self.organisation},
        )

        self.assertTrue(form.is_valid())
        self.assertEqual("test@test.test", form.cleaned_data["email"])

    def test_email_conseiller_numerique(self):
        form = get_form(
            ReferentForm,
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
            AidantRequestForm,
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
            AidantRequestForm,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            email=organisation.manager.email,
        )

        self.assertTrue(form.is_valid())

    def test_clean_aidant_with_same_email_as_another_aidant(self):
        organisation = OrganisationRequestFactory()
        aidant = AidantRequestFactory(organisation=organisation)
        form = get_form(
            AidantRequestForm,
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
            AidantRequestForm,
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
            AidantRequestForm,
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
            AidantRequestForm,
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
            AidantRequestForm,
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

    def test_aidant_request_with_validated_organisation_create_habiliation_request(
        self,
    ):
        real_organisation = OrganisationFactory(name="real Organisation")
        organisation = OrganisationRequestFactory()
        organisation.organisation = real_organisation
        organisation.save()
        form = get_form(
            AidantRequestForm,
            ignore_errors=True,
            form_init_kwargs={"organisation": organisation},
            conseiller_numerique=False,
            email="aidant_with_hr@test.fr",
        )
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(
            HabilitationRequest.objects.filter(
                organisation=real_organisation, email="aidant_with_hr@test.fr"
            ).exists()
        )


class TestAidantRequestFormSet(TestCase):
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
