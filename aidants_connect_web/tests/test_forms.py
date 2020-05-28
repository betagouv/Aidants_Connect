from django.forms.models import model_to_dict
from django.test import tag, TestCase
from django.test.client import Client

from aidants_connect_web.forms import (
    AidantCreationForm,
    AidantChangeForm,
    MandatForm,
    RecapMandatForm,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


@tag("forms")
class AidantCreationFormTests(TestCase):
    def setUp(self):
        self.data = {
            "first_name": "Heliette",
            "last_name": "Bernart",
            "email": "hbernart@domain.user",
            "username": "",
            "password": "hdryjsydjsydjsydj",
            "profession": "Mediatrice",
            "organisation": "3",
        }
        self.organisation = OrganisationFactory(id=3)
        self.existing_aidant = AidantFactory(
            first_name="Armand",
            last_name="Giraud",
            email="agiraud@domain.user",
            username="agiraud@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisation=self.organisation,
        )

    def test_from_renders_item_text_input(self):
        form = AidantCreationForm()
        self.assertIn("Email", form.as_p())

    def test_errors_for_blank_items(self):
        def field_test(name_of_field: str, data_set: dict) -> None:
            data_set[name_of_field] = ""
            form = AidantCreationForm(data=data_set)
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors[name_of_field], ["Ce champ est obligatoire."])

        for field in [
            "password",
            "email",
            "last_name",
            "first_name",
            "profession",
            "organisation",
        ]:
            field_test(field, self.data.copy())

    def test_validation_for_all_items(self):
        form = AidantCreationForm(data=self.data.copy())
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Aidant.objects.all().count(), 2)
        new_aidant = Aidant.objects.get(email="hbernart@domain.user")
        self.assertEqual(new_aidant.username, "hbernart@domain.user")

    def test_cannot_create_new_aidant_with_same_email(self):
        AidantFactory(
            first_name="Henri",
            last_name="Bernart",
            email="hbernart@domain.user",
            username="hbernart@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisation=self.organisation,
        )

        form = AidantCreationForm(data=self.data)
        self.assertFalse(form.is_valid())

    def test_cannot_create_new_aidant_with_unsound_password(self):
        data_set = self.data.copy()

        # settings.py AUTH_PASSWORD_VALIDATORS.MinimumLengthValidator
        data_set["password"] = "lala"
        form = AidantCreationForm(data=data_set)
        self.assertFalse(form.is_valid())

        # settings.py AUTH_PASSWORD_VALIDATORS.CommonPasswordValidator
        data_set["password"] = "password"
        form = AidantCreationForm(data=data_set)
        self.assertFalse(form.is_valid())

        # settings.py AUTH_PASSWORD_VALIDATORS.UserAttributeSimilarityValidator
        data_set["password"] = "Bernart"
        form = AidantCreationForm(data=data_set)
        self.assertFalse(form.is_valid())

        # settings.py AUTH_PASSWORD_VALIDATORS.NumericPasswordValidator
        data_set["password"] = "1234567890"
        form = AidantCreationForm(data=data_set)
        self.assertFalse(form.is_valid())


class AidantChangeFormTests(TestCase):
    def setUp(self):
        self.organisation_nantes = OrganisationFactory(
            name="Association Aide au Numérique"
        )
        self.organisation_nantes = OrganisationFactory(name="Association Aide'o'Web")
        self.nantes_id = self.organisation_nantes.id
        AidantFactory(
            first_name="Henri",
            last_name="Bernard",
            email="hello@domain.user",
            username="hello@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisation=self.organisation_nantes,
        )
        self.aidant2 = AidantFactory(
            first_name="Armand",
            last_name="Bernard",
            email="abernart@domain.user",
            username="abernart@domain.user",
            profession="Mediateur",
            organisation=self.organisation_nantes,
        )
        self.aidant2.set_password("nananana")

    def test_change_email_propagates_to_username(self):
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")
        self.assertEqual(self.aidant2.first_name, "Armand")

        changed_data = {
            "first_name": "Armand",
            "last_name": "Bernart",
            "username": "abernart@domain.user",
            "email": "goodbye@domain.user",
            "profession": "Mediateur",
            "organisation": self.nantes_id,
        }
        form = AidantChangeForm(
            data=changed_data,
            initial=model_to_dict(self.aidant2),
            instance=self.aidant2,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(self.aidant2.email, "goodbye@domain.user")
        self.assertEqual(self.aidant2.username, "goodbye@domain.user")
        self.assertEqual(self.aidant2.first_name, "Armand")
        form.save()
        self.assertCountEqual(form.errors, [])

    def test_change_date_propagates_to_aidant_profile(self):
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")
        self.assertEqual(self.aidant2.first_name, "Armand")

        changed_data = {
            "first_name": "Armand",
            "last_name": "test",
            "username": "abernart@domain.user",
            "email": "abernart@domain.user",
            "profession": "Mediateur",
            "organisation": self.nantes_id,
        }
        form = AidantChangeForm(
            data=changed_data,
            initial=model_to_dict(self.aidant2),
            instance=self.aidant2,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")
        self.assertEqual(self.aidant2.last_name, "test")

    def test_change_to_email_fails_if_email_exists(self):
        changed_data = {
            "first_name": "Armand",
            "last_name": "Bernart",
            "username": "abernart@domain.user",
            "email": "hello@domain.user",
            "profession": "Mediateur",
            "organisation": "4",
        }

        form = AidantChangeForm(
            data=changed_data,
            initial=model_to_dict(self.aidant2),
            instance=self.aidant2,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")
        self.assertEqual(form.errors["email"], ["This email is already taken"])


class MandatFormTests(TestCase):
    def test_form_renders_item_text_input(self):
        form = MandatForm()
        self.assertIn("argent", form.as_p())

    def test_validation_for_blank_items(self):
        form = MandatForm(data={"demarche": ["argent"], "duree": "SHORT"})
        self.assertTrue(form.is_valid())

        form_2 = MandatForm(data={"demarche": [], "duree": "SHORT"})
        self.assertFalse(form_2.is_valid())
        self.assertEqual(form_2.errors["demarche"], ["Ce champ est obligatoire."])

        form_3 = MandatForm(data={"demarche": ["travail"], "duree": ""})
        self.assertFalse(form_3.is_valid())
        self.assertEqual(form_3.errors["duree"], ["Ce champ est obligatoire."])

    def test_non_existing_demarche_triggers_error(self):
        form = MandatForm(data={"demarche": ["test"], "duree": "16"})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["demarche"],
            ["Sélectionnez un choix valide. test n’en fait pas partie."],
        )

    def test_non_integer_duree_triggers_error(self):
        form = MandatForm(data={"demarche": ["argent"], "duree": "test"})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["duree"],
            ["Sélectionnez un choix valide. test n’en fait pas partie."],
        )


class RecapMandatFormTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = AidantFactory()
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")

    def test_form_renders_item_text_input(self):
        self.client.force_login(self.aidant_thierry)
        form = RecapMandatForm(aidant=self.aidant_thierry)
        self.assertIn("autorise", form.as_p())

    def test_valid_form(self):
        self.client.force_login(self.aidant_thierry)
        form_1 = RecapMandatForm(
            aidant=self.aidant_thierry,
            data={"brief": ["on"], "personal_data": ["on"], "otp_token": "123456"},
        )
        self.assertTrue(form_1.is_valid())

    def test_repeat_token_is_not_valid(self):
        self.client.force_login(self.aidant_thierry)
        form_1 = RecapMandatForm(
            aidant=self.aidant_thierry,
            data={"brief": ["on"], "personal_data": ["on"], "otp_token": "123456"},
        )
        form_1.is_valid()
        form_2 = RecapMandatForm(
            aidant=self.aidant_thierry,
            data={"brief": ["on"], "personal_data": ["on"], "otp_token": "123456"},
        )
        self.assertFalse(form_2.is_valid())
