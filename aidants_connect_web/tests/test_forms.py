from django.test import TestCase

from aidants_connect_web.forms import UsagerForm


class UsagerFormTest(TestCase):
    def test_from_renders_item_text_input(self):
        form = UsagerForm()
        self.assertIn("Prénoms", form.as_p())

    def test_validation_for_blank_items(self):
        form = UsagerForm(data={"given_name": ""})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["given_name"],
            ["Le champs Prénoms est obligatoire. Ex : Camille-Marie Claude Dominique"],
        )
