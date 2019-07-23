from django.test import TestCase

from aidants_connect_web.forms import UserCreationForm


class UserCreationFormTest(TestCase):
    def setUp(self):
        self.data = {
            "first_name": "Heliette",
            "last_name": "bernart",
            "email": "abernart@domain.user",
            "password": "hdryjsydjsydjsydj",
            "profession": "Mediatrice",
            "organisme": "Bibliothèque Dumas",
            "ville": "Vernon",
        }

    def test_from_renders_item_text_input(self):
        form = UserCreationForm()
        self.assertIn("Email", form.as_p())

    def test_validation_for_blank_items(self):
        def field_test(name_of_field):
            data_set = {
                "first_name": "Heliette",
                "last_name": "bernart",
                "email": "abernart@domain.user",
                "password": "hdryjsydjsydjsydj",
                "profession": "Mediatrice",
                "organisme": "Bibliothèque Dumas",
                "ville": "Vernon",
            }
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
            field_test(field)

    def test_validation_for_all_items(self):
        form = UserCreationForm(data=self.data)
        print(form.errors)
        self.assertTrue(form.is_valid())
