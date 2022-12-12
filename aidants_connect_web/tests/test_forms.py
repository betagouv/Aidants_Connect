from django.forms.models import model_to_dict
from django.test import TestCase, tag
from django.test.client import Client

from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.forms import (
    AidantChangeForm,
    AidantCreationForm,
    DatapassHabilitationForm,
    MandatForm,
    MassEmailHabilitatonForm,
    RecapMandatForm,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


@tag("forms")
class AidantCreationFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = {
            "first_name": "Heliette",
            "last_name": "Bernart",
            "email": "hbernart@domain.user",
            "username": "",
            "password": "hdryjsydjsydjsydj",
            "profession": "Mediatrice",
            "organisation": "3",
        }
        cls.organisation = OrganisationFactory(id=3)
        cls.existing_aidant = AidantFactory(
            first_name="Armand",
            last_name="Giraud",
            email="agiraud@domain.user",
            username="agiraud@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisation=cls.organisation,
        )

    def test_from_renders_item_text_input(self):
        form = AidantCreationForm()
        self.assertIn("Email", form.as_p())

    def test_errors_for_blank_items(self):
        def field_test(name_of_field: str, data_set: dict) -> None:
            data_set[name_of_field] = ""
            form = AidantCreationForm(data=data_set)
            self.assertFalse(
                form.is_valid(),
                f"Field {name_of_field} is considered valid, it should not.",
            )
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
    @classmethod
    def setUpTestData(cls):
        cls.organisation_nantes = OrganisationFactory(
            name="Association Aide au Numérique"
        )
        cls.organisation_nantes = OrganisationFactory(name="Association Aide'o'Web")
        cls.nantes_id = cls.organisation_nantes.id
        AidantFactory(
            first_name="Henri",
            last_name="Bernard",
            email="hello@domain.user",
            username="hello@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisation=cls.organisation_nantes,
        )
        cls.aidant2 = AidantFactory(
            first_name="Armand",
            last_name="Bernard",
            email="abernart@domain.user",
            username="abernart@domain.user",
            profession="Mediateur",
            organisation=cls.organisation_nantes,
        )
        cls.aidant2.set_password("nananana")

    def test_change_email_propagates_to_username(self):
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")

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
        self.aidant2.refresh_from_db()
        self.assertEqual(self.aidant2.first_name, "Armand")
        self.assertEqual(self.aidant2.email, "abernart@domain.user")
        self.assertEqual(self.aidant2.username, "abernart@domain.user")

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
        self.aidant2.refresh_from_db()
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

    def test_you_can_update_email_to_match_username(self):
        aidant = AidantFactory(
            email="wrong@mail.net",
            username="good@mail.net",
        )
        changed_data = {
            "username": "good@mail.net",
            "email": "good@mail.net",
            "first_name": aidant.first_name,
            "last_name": aidant.last_name,
            "profession": "Mediateur",
            "organisation": str(aidant.organisation.id),
        }
        form = AidantChangeForm(
            data=changed_data,
            initial=model_to_dict(aidant),
            instance=aidant,
        )

        aidant.refresh_from_db()
        self.assertTrue(form.is_valid())
        self.assertEqual(aidant.email, "good@mail.net")
        self.assertEqual(aidant.username, "good@mail.net")

    def test_you_can_update_username_to_match_email(self):
        aidant = AidantFactory(
            email="good@mail.net",
            username="wrong@mail.net",
        )
        changed_data = {
            "username": "good@mail.net",
            "email": "good@mail.net",
            "first_name": aidant.first_name,
            "last_name": aidant.last_name,
            "profession": "Mediateur",
            "organisation": str(aidant.organisation.id),
        }
        form = AidantChangeForm(
            data=changed_data,
            initial=model_to_dict(aidant),
            instance=aidant,
        )

        aidant.refresh_from_db()
        self.assertTrue(form.is_valid())
        self.assertEqual(aidant.email, "good@mail.net")
        self.assertEqual(aidant.username, "good@mail.net")


class MandatFormTests(TestCase):
    def test_form_renders_item_text_input(self):
        form = MandatForm()
        self.assertIn("argent", form.as_p())

    def test_validation_for_blank_items(self):
        form = MandatForm(data={"demarche": ["argent"], "duree": "SHORT"})
        self.assertTrue(form.is_valid())

        form_2 = MandatForm(data={"demarche": [], "duree": "SHORT"})
        self.assertFalse(form_2.is_valid())
        self.assertListEqual(
            form_2.errors["demarche"],
            ["Vous devez sélectionner au moins une démarche."],
        )

        form_3 = MandatForm(data={"demarche": ["travail"], "duree": ""})
        self.assertFalse(form_3.is_valid())
        self.assertListEqual(
            form_3.errors["duree"], ["Veuillez sélectionner la durée du mandat."]
        )

        form_4 = MandatForm(
            data={"demarche": ["travail"], "duree": "SHORT", "is_remote": True}
        )
        self.assertFalse(form_4.is_valid())
        self.assertListEqual(
            form_4.errors["remote_constent_method"],
            [
                "Vous devez choisir parmis l'une des "
                "méthodes de consentement à distance."
            ],
        )

        form_5 = MandatForm(
            data={
                "demarche": ["travail"],
                "duree": "SHORT",
                "is_remote": True,
                "remote_constent_method": RemoteConsentMethodChoices.LEGACY.name,
            }
        )
        self.assertTrue(form_5.is_valid())

        form_6 = MandatForm(
            data={
                "demarche": ["travail"],
                "duree": "SHORT",
                "is_remote": True,
                "remote_constent_method": RemoteConsentMethodChoices.SMS.name,
            }
        )
        self.assertFalse(form_6.is_valid())
        self.assertListEqual(
            form_6.errors["user_phone"],
            [
                "Un numéro de téléphone est obligatoire "
                "si le consentement est demandé par SMS."
            ],
        )

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

    def test_remote_fields_emptied_when_mandate_is_not_remote(self):
        # Remote mandate related fields a cleaned when mandate is not remote
        form = MandatForm(
            data={
                "demarche": ["argent"],
                "duree": "SHORT",
                "is_remote": False,
                "remote_constent_method": RemoteConsentMethodChoices.SMS.name,
                "user_phone": "0 800 840 800",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual("", form.cleaned_data["remote_constent_method"])
        self.assertEqual("", form.cleaned_data["user_phone"])

        # Remote mandate related fields a cleaned when mandate is not remote
        form = MandatForm(
            data={
                "demarche": ["argent"],
                "duree": "SHORT",
                "is_remote": True,
                "remote_constent_method": RemoteConsentMethodChoices.LEGACY.name,
                "user_phone": "0 800 840 800",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual("", form.cleaned_data["user_phone"])


class RecapMandatFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant_thierry = AidantFactory()
        device = cls.aidant_thierry.staticdevice_set.create(id=1)
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


@tag("forms")
class DatapassAccreditationFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory(data_pass_id=42)

    def test_raise_error_with_invalid_data_pass_id(self):
        form = DatapassHabilitationForm(
            data={
                "first_name": "Mario",
                "last_name": "Brosse",
                "email": "mario.brossse@world.fr",
                "profession": "plombier",
                "data_pass_id": 33,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["data_pass_id"], ["No organisation for data_pass_id"]
        )

    def test_forms_is_ok(self):
        form = DatapassHabilitationForm(
            data={
                "first_name": "Mario",
                "last_name": "Brosse",
                "email": "mario.brossse@world.fr",
                "profession": "plombier",
                "data_pass_id": 42,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["organisation"], self.organisation)

        habilitation = form.save()

        self.assertEqual(habilitation.organisation, self.organisation)
        self.assertEqual(habilitation.first_name, "Mario")
        self.assertEqual(habilitation.last_name, "Brosse")
        self.assertEqual(habilitation.email, "mario.brossse@world.fr")
        self.assertEqual(habilitation.profession, "plombier")


@tag("forms")
class MassEmailHabilitatonFormTests(TestCase):
    def test_filter_empty_values(self):
        form = MassEmailHabilitatonForm(
            data={
                "email_list": """toto@tata.net

                titi@lala.net""",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["email_list"], {"toto@tata.net", "titi@lala.net"}
        )

    def test_ok_with_only_one_email(self):
        form = MassEmailHabilitatonForm(
            data={
                "email_list": "toto@tata.net",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email_list"], {"toto@tata.net"})

    def test_reject_non_email_strings(self):
        form = MassEmailHabilitatonForm(
            data={
                "email_list": """gabuzomeu
                titi@lala.net""",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["email_list"],
            ["Veuillez saisir uniquement des adresses e-mail valides."],
        )

    def test_reject_invalid_emails(self):
        form = MassEmailHabilitatonForm(
            data={
                "email_list": """josée@accent.com
                titi@lala.net""",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["email_list"],
            ["Veuillez saisir uniquement des adresses e-mail valides."],
        )
