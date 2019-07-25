from django.test import TestCase

from aidants_connect_web.forms import UserCreationForm, UserChangeForm
from aidants_connect_web.models import User


class UserCreationFormTest(TestCase):
    def setUp(self):
        self.data = {
            "first_name": "Heliette",
            "last_name": "Bernart",
            "email": "hbernart@domain.user",
            "username": "",
            "password": "hdryjsydjsydjsydj",
            "profession": "Mediatrice",
            "organisme": "Bibliothèque Dumas",
            "ville": "Vernon",
        }
        self.existing_user = User.objects.create(
            first_name="Armand",
            last_name="Giraud",
            email="agiraud@domain.user",
            username="agiraud@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisme="Association Aide au Numérique",
            ville="Nîmes",
        )

    def test_from_renders_item_text_input(self):
        form = UserCreationForm()
        self.assertIn("Email", form.as_p())

    def test_errors_for_blank_items(self):
        def field_test(name_of_field: str, data_set: dict) -> None:
            data_set[name_of_field] = ""
            form = UserCreationForm(data=data_set)
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors[name_of_field], ["Ce champ est obligatoire."])

        for field in [
            "password",
            "email",
            "last_name",
            "first_name",
            "profession",
            "organisme",
            "ville",
        ]:
            field_test(field, self.data.copy())

    def test_validation_for_all_items(self):
        form = UserCreationForm(data=self.data.copy())
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(User.objects.all().count(), 2)
        new_user = User.objects.get(email="hbernart@domain.user")
        self.assertEqual(new_user.username, "hbernart@domain.user")

    def test_cannot_create_new_user_with_same_email(self):
        User.objects.create(
            first_name="Henri",
            last_name="Bernart",
            email="hbernart@domain.user",
            username="hbernart@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisme="Association Aide au Numérique",
            ville="Nîmes",
        )

        form = UserCreationForm(data=self.data)
        self.assertFalse(form.is_valid())

    def test_cannot_create_new_user_with_unsound_password(self):
        data_set = self.data.copy()

        # settings.py AUTH_PASSWORD_VALIDATORS.MinimumLengthValidator
        data_set["password"] = "lala"
        form = UserCreationForm(data=data_set)
        self.assertFalse(form.is_valid())

        # settings.py AUTH_PASSWORD_VALIDATORS.CommonPasswordValidator
        data_set["password"] = "password"
        form = UserCreationForm(data=data_set)
        self.assertFalse(form.is_valid())

        # settings.py AUTH_PASSWORD_VALIDATORS.UserAttributeSimilarityValidator
        data_set["password"] = "Bernart"
        form = UserCreationForm(data=data_set)
        self.assertFalse(form.is_valid())

        # settings.py AUTH_PASSWORD_VALIDATORS.NumericPasswordValidator
        data_set["password"] = "1234567890"
        form = UserCreationForm(data=data_set)
        self.assertFalse(form.is_valid())


class UserChangeFormTest(TestCase):
    def setUp(self):
        User.objects.create(
            first_name="Henri",
            last_name="Bernard",
            email="hello@domain.user",
            username="hello@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisme="Association Aide au Numérique",
            ville="Nîmes",
        )
        self.aidant2 = User.objects.create(
            first_name="Armand",
            last_name="Bernard",
            email="abernart@domain.user",
            username="abernart@domain.user",
            password="fkgjfdùkqbnqùfkn",
            profession="Mediateur",
            organisme="Association Aide'o'Web",
            ville="Nantes",
        )

    def test_change_email_propergates_to_username(self):
        self.assertEqual(self.aidant2.first_name, "Armand")

        form = UserChangeForm(
            data={
                "first_name": "Armand",
                "last_name": "Bernart",
                "username": "abernart@domain.user",
                "email": "goodbye@domain.user",
                "profession": "Mediateur",
                "organisme": "Association Aide'o'Web",
                "ville": "Nantes",
            }
        )
        form.instance = self.aidant2
        self.assertTrue(form.is_valid())
        self.assertEqual(self.aidant2.email, "goodbye@domain.user")
        self.assertEqual(self.aidant2.username, "goodbye@domain.user")
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.password, "fkgjfdùkqbnqùfkn")

    def test_change_to_email_fails_if_email_exists(self):

        form = UserChangeForm(
            data={
                "first_name": "Armand",
                "last_name": "Bernart",
                "username": "abernart@domain.user",
                "email": "hello@domain.user",
                "profession": "Mediateur",
                "organisme": "Association Aide'o'Web",
                "ville": "Nantes",
            }
        )
        form.instance = self.aidant2
        self.assertFalse(form.is_valid())
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")
        self.assertEqual(form.errors["email"], ["This email is already taken"])
