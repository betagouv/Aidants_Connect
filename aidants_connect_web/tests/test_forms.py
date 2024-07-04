from unittest import mock
from unittest.mock import Mock

from django.forms.models import model_to_dict, modelformset_factory
from django.test import TestCase, override_settings, tag
from django.test.client import Client

from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.constants import (
    OTP_APP_DEVICE_NAME,
    RemoteConsentMethodChoices,
)
from aidants_connect_web.forms import (
    AddAppOTPToAidantForm,
    AidantChangeForm,
    AidantCreationForm,
    DatapassHabilitationForm,
    HabilitationRequestCreationForm,
    HabilitationRequestCreationFormSet,
    MandatForm,
    MassEmailActionForm,
    RecapMandatForm,
    get_choices_for_remote_method,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import (
    AidantFactory,
    OrganisationFactory,
    UsagerFactory,
)


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


class SMSConsentFeatureFlagsTests(TestCase):
    @override_settings(FF_ACTIVATE_SMS_CONSENT=False)
    def test_not_sms_method_when_ff_sms_is_false(self):
        remote_method = get_choices_for_remote_method()
        self.assertFalse(
            any(
                [
                    key == RemoteConsentMethodChoices.SMS.name
                    for key, value in remote_method
                ]
            )
        )

    @override_settings(FF_ACTIVATE_SMS_CONSENT=True)
    def test_sms_method_present_when_ff_sms_is_true(self):
        remote_method = get_choices_for_remote_method()
        self.assertTrue(
            any(
                [
                    key == RemoteConsentMethodChoices.SMS.name
                    for key, value in remote_method
                ]
            )
        )


class MandatFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory()
        cls.organisation_with_disallowed_characters = OrganisationFactory(
            allowed_demarches=["papiers", "famille", "social"]
        )
        super().setUpTestData()

    def test_form_renders_item_text_input(self):
        form = MandatForm(self.organisation)
        self.assertIn("argent", form.as_p())

    def test_validation_for_blank_items(self):
        form = MandatForm(
            self.organisation, data={"demarche": ["argent"], "duree": "SHORT"}
        )
        self.assertTrue(form.is_valid())

        form_2 = MandatForm(self.organisation, data={"demarche": [], "duree": "SHORT"})
        self.assertFalse(form_2.is_valid())
        self.assertListEqual(
            form_2.errors["demarche"],
            ["Vous devez sélectionner au moins une démarche."],
        )

        form_3 = MandatForm(
            self.organisation, data={"demarche": ["travail"], "duree": ""}
        )
        self.assertFalse(form_3.is_valid())
        self.assertListEqual(
            form_3.errors["duree"], ["Veuillez sélectionner la durée du mandat."]
        )

        form_4 = MandatForm(
            self.organisation,
            data={"demarche": ["travail"], "duree": "SHORT", "is_remote": True},
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
            self.organisation,
            data={
                "demarche": ["travail"],
                "duree": "SHORT",
                "is_remote": True,
                "remote_constent_method": RemoteConsentMethodChoices.LEGACY.name,
            },
        )
        self.assertTrue(form_5.is_valid())

        form_6 = MandatForm(
            self.organisation,
            data={
                "demarche": ["travail"],
                "duree": "SHORT",
                "is_remote": True,
                "remote_constent_method": RemoteConsentMethodChoices.SMS.name,
            },
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
        form = MandatForm(
            self.organisation, data={"demarche": ["test"], "duree": "SHORT"}
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["demarche"],
            ["Sélectionnez un choix valide. test n’en fait pas partie."],
        )

    def test_non_integer_duree_triggers_error(self):
        form = MandatForm(
            self.organisation, data={"demarche": ["argent"], "duree": "test"}
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["duree"],
            ["Sélectionnez un choix valide. test n’en fait pas partie."],
        )

    def test_remote_fields_emptied_when_mandate_is_not_remote(self):
        # Remote mandate related fields a cleaned when mandate is not remote
        form = MandatForm(
            self.organisation,
            data={
                "demarche": ["argent"],
                "duree": "SHORT",
                "is_remote": False,
                "remote_constent_method": RemoteConsentMethodChoices.SMS.name,
                "user_phone": "0 800 840 800",
            },
        )
        self.assertTrue(form.is_valid())
        self.assertEqual("", form.cleaned_data["remote_constent_method"])
        self.assertEqual("", form.cleaned_data["user_phone"])

        # Remote mandate related fields a cleaned when mandate is not remote
        form = MandatForm(
            self.organisation,
            data={
                "demarche": ["argent"],
                "duree": "SHORT",
                "is_remote": True,
                "remote_constent_method": RemoteConsentMethodChoices.LEGACY.name,
                "user_phone": "0 800 840 800",
            },
        )
        self.assertTrue(form.is_valid())
        self.assertEqual("", form.cleaned_data["user_phone"])

    def test_disallowed_demarche_triggers_error(self):
        form = MandatForm(
            self.organisation_with_disallowed_characters,
            data={"demarche": ["argent"], "duree": "SHORT"},
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ["Sélectionnez un choix valide. argent n’en fait pas partie."],
            form.errors["demarche"],
        )
        form = MandatForm(
            self.organisation_with_disallowed_characters,
            data={
                "demarche": ["papiers", "argent", "transports", "justice"],
                "duree": "SHORT",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            "Sélectionnez un choix valide. argent n’en fait pas partie.",
            form.errors["demarche"][0],
        )


class RecapMandatFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant_thierry = AidantFactory()
        cls.usager = UsagerFactory()
        device = cls.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")

    def test_valid_form(self):
        self.client.force_login(self.aidant_thierry)
        form_1 = RecapMandatForm(
            aidant=self.aidant_thierry,
            usager=self.usager,
            data={"brief": ["on"], "personal_data": ["on"], "otp_token": "123456"},
        )
        self.assertTrue(form_1.is_valid())

    def test_repeat_token_is_not_valid(self):
        self.client.force_login(self.aidant_thierry)
        form_1 = RecapMandatForm(
            aidant=self.aidant_thierry,
            usager=self.usager,
            data={"brief": ["on"], "personal_data": ["on"], "otp_token": "123456"},
        )
        form_1.is_valid()
        form_2 = RecapMandatForm(
            aidant=self.aidant_thierry,
            usager=self.usager,
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
        form = MassEmailActionForm(
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
        form = MassEmailActionForm(
            data={
                "email_list": "toto@tata.net",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email_list"], {"toto@tata.net"})

    def test_reject_non_email_strings(self):
        form = MassEmailActionForm(
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
        form = MassEmailActionForm(
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


class TestAddAppOTPToAidantForm(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant = AidantFactory()
        cls.otp_device = TOTPDevice(
            user=cls.aidant,
            name=OTP_APP_DEVICE_NAME % cls.aidant.pk,
            confirmed=False,
        )

    @mock.patch.object(TOTP, "verify")
    def test_clean_otp_token(self, mock_verify: Mock):
        form = AddAppOTPToAidantForm(self.otp_device, data={"otp_token": "1"})
        self.assertFalse(form.is_valid())

        self.assertEqual(
            [
                (
                    "Assurez-vous que cette valeur comporte "
                    "au moins 6 caractères (actuellement 1)."
                )
            ],
            form.errors["otp_token"],
        )

        form = AddAppOTPToAidantForm(self.otp_device, data={"otp_token": "12345678910"})
        self.assertFalse(form.is_valid())

        self.assertEqual(
            [
                (
                    "Assurez-vous que cette valeur comporte "
                    "au plus 8 caractères (actuellement 11)."
                )
            ],
            form.errors["otp_token"],
        )

        mock_verify.return_value = False
        form = AddAppOTPToAidantForm(self.otp_device, data={"otp_token": "654321"})

        self.assertFalse(form.is_valid())
        self.assertEqual(
            ["La vérification du code OTP a échoué"], form.errors["otp_token"]
        )

        mock_verify.return_value = True
        form = AddAppOTPToAidantForm(self.otp_device, data={"otp_token": "123456"})

        self.assertTrue(form.is_valid())


@tag("forms")
class HabilitationRequestCreationFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory()
        OrganisationFactory()
        OrganisationFactory()
        cls.referent = AidantFactory(
            first_name="Armand",
            last_name="Giraud",
            email="agiraud@domain.user",
            username="agiraud@domain.user",
            password="flkqgnfdùqlgnqùflkgnùqflkngw",
            profession="Mediateur",
            organisation=cls.organisation,
        )
        cls.referent.responsable_de.add(cls.organisation)

    def test_filter_queryset_organisation(self):
        form = HabilitationRequestCreationForm(referent=self.referent)
        self.assertEqual(1, form.fields["organisation"].queryset.count())


@tag("forms")
class TestHabilitationRequestCreationFormSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent = AidantFactory(post__is_organisation_manager=True)
        cls.form_cls = modelformset_factory(
            HabilitationRequestCreationForm.Meta.model,
            HabilitationRequestCreationForm,
            formset=HabilitationRequestCreationFormSet,
        )

    def test_form_has_temp_data(self):
        # First case: no data bound
        form = self.form_cls(
            force_left_form_check=False, form_kwargs={"referent": self.referent}
        )
        self.assertFalse(form.has_temp_data)

        # Second case: has data but not blank left_form
        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": "",
                "form-0-email": "test@test.test",
                "form-0-first_name": "Sarah",
                "form-0-last_name": "Lambda",
                "form-0-profession": "organisatrice",
                "form-0-organisation": f"{self.referent.organisation.pk}",
                "form-0-conseiller_numerique": "False",
            },
        )
        self.assertFalse(form.has_temp_data)

        # Third case: has at least one left_form field in its data
        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": "",
                "form-0-email": "test@test.test",
                "form-0-first_name": "Sarah",
                "form-0-last_name": "Lambda",
                "form-0-profession": "organisatrice",
                "form-0-organisation": f"{self.referent.organisation.pk}",
                "form-0-conseiller_numerique": "False",
                "form-__temp__-last_name": "",
                "form-__temp__-profession": "animateurice",
            },
        )
        self.assertTrue(form.has_temp_data)

    def test_left_form_empty_permitted_no_data(self):
        # We don't want to force validate the left_form if no data is present
        form = self.form_cls(
            force_left_form_check=False, form_kwargs={"referent": self.referent}
        )
        self.assertTrue(form.left_form.empty_permitted)

        form = self.form_cls(
            force_left_form_check=True, form_kwargs={"referent": self.referent}
        )
        self.assertTrue(form.left_form.empty_permitted)

    def test_left_form_empty_permitted_no_left_form(self):
        # Data is submitted, but none corresponding to left_form
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": "",
            "form-0-email": "test@test.test",
            "form-0-first_name": "Sarah",
            "form-0-last_name": "Lambda",
            "form-0-profession": "organisatrice",
            "form-0-organisation": f"{self.referent.organisation.pk}",
            "form-0-conseiller_numerique": "False",
        }

        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertTrue(form.left_form.empty_permitted)

        form = self.form_cls(
            force_left_form_check=True,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertTrue(form.left_form.empty_permitted)

    def test_left_form_empty_permitted_with_left_form(self):
        # Data is submitted, with left_form data

        # First case: left_form is the first submitted form, we want to force check
        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "0",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-__temp__-id": "",
                "form-__temp__-email": "",
                "form-__temp__-first_name": "",
                "form-__temp__-last_name": "",
                "form-__temp__-profession": "",
                "form-__temp__-organisation": "",
                "form-__temp__-conseiller_numerique": "",
            },
        )
        self.assertFalse(form.left_form.empty_permitted)

        # Second case: form has data and force_left_form_check is True
        form = self.form_cls(
            force_left_form_check=True,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": "",
                "form-0-email": "test@test.test",
                "form-0-first_name": "Sarah",
                "form-0-last_name": "Lambda",
                "form-0-profession": "organisatrice",
                "form-0-organisation": f"{self.referent.organisation.pk}",
                "form-0-conseiller_numerique": "False",
            },
        )
        self.assertTrue(form.left_form.empty_permitted)

        # Third case: same as before, with blank left_form submitted
        form = self.form_cls(
            force_left_form_check=True,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": "",
                "form-0-email": "test@test.test",
                "form-0-first_name": "Sarah",
                "form-0-last_name": "Lambda",
                "form-0-profession": "organisatrice",
                "form-0-organisation": f"{self.referent.organisation.pk}",
                "form-0-conseiller_numerique": "False",
                "form-__temp__-id": "",
                "form-__temp__-email": "",
                "form-__temp__-first_name": "",
                "form-__temp__-last_name": "",
                "form-__temp__-profession": "",
                "form-__temp__-organisation": "",
                "form-__temp__-conseiller_numerique": "",
            },
        )
        self.assertFalse(form.left_form.empty_permitted)

    def test_is_valid_left_form_is_not_valid(self):
        # First case: empty form is not valid
        form = self.form_cls(
            force_left_form_check=True,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "0",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-__temp__-id": "",
                "form-__temp__-email": "",
                "form-__temp__-first_name": "",
                "form-__temp__-last_name": "",
                "form-__temp__-profession": "",
                "form-__temp__-organisation": "",
                "form-__temp__-conseiller_numerique": "",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(0, len(form.forms))
        self.assertEqual(
            {
                "email": [{"message": "Ce champ est obligatoire.", "code": "required"}],
                "first_name": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "last_name": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "profession": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "organisation": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "conseiller_numerique": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
            },
            form.left_form.errors.get_json_data(),
        )

    def test_is_valid_filled_form_is_valid(self):
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": "",
            "form-0-email": "test@test.test",
            "form-0-first_name": "Sarah",
            "form-0-last_name": "Lambda",
            "form-0-profession": "organisatrice",
            "form-0-organisation": f"{self.referent.organisation.pk}",
            "form-0-conseiller_numerique": "False",
        }

        # First case, force_left_form_check is False
        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(1, len(form.forms))

        # Second case, force_left_form_check is True but no __temp__ data is present
        form = self.form_cls(
            force_left_form_check=True,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(1, len(form.forms))

    def test_is_valid_check_left_form(self):
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": "",
            "form-0-email": "test@test.test",
            "form-0-first_name": "Sarah",
            "form-0-last_name": "Lambda",
            "form-0-profession": "organisatrice",
            "form-0-organisation": f"{self.referent.organisation.pk}",
            "form-0-conseiller_numerique": "False",
            "form-__temp__-id": "",
            "form-__temp__-email": "",
            "form-__temp__-first_name": "",
            "form-__temp__-last_name": "",
            "form-__temp__-profession": "",
            "form-__temp__-organisation": "",
            "form-__temp__-conseiller_numerique": "",
        }

        # Case 1, we don't want to force check empty form
        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(1, len(form.forms))
        self.assertEqual(data, form.data)
        self.assertEqual(
            [
                {
                    "conseiller_numerique": False,
                    "email": "test@test.test",
                    "first_name": "Sarah",
                    "id": None,
                    "last_name": "Lambda",
                    "organisation": self.referent.organisation,
                    "profession": "organisatrice",
                }
            ],
            form.cleaned_data,
        )

        # Case 2, we want to force check empty form
        form = self.form_cls(
            force_left_form_check=True,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(1, len(form.forms))
        self.assertEqual(
            {
                "email": [{"message": "Ce champ est obligatoire.", "code": "required"}],
                "first_name": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "last_name": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "profession": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "organisation": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
                "conseiller_numerique": [
                    {"message": "Ce champ est obligatoire.", "code": "required"}
                ],
            },
            form.left_form.errors.get_json_data(),
        )
        self.assertRaises(AttributeError, getattr, form, "cleaned_data")

    def test_is_valid_filled_left_form_is_added_to_forms(self):
        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data={
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": "",
                "form-0-email": "test@test.test",
                "form-0-first_name": "Sarah",
                "form-0-last_name": "Lambda",
                "form-0-profession": "organisateurice",
                "form-0-organisation": f"{self.referent.organisation.pk}",
                "form-0-conseiller_numerique": "False",
                "form-__temp__-id": "",
                "form-__temp__-email": "test2@test.test",
                "form-__temp__-first_name": "Abdel",
                "form-__temp__-last_name": "Sigma",
                "form-__temp__-profession": "organisateurice",
                "form-__temp__-organisation": f"{self.referent.organisation.pk}",
                "form-__temp__-conseiller_numerique": "False",
            },
        )
        self.assertEqual(1, len(form.forms))
        self.assertTrue(form.is_valid())
        self.assertEqual(2, len(form.forms))
        self.assertEqual(
            {
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": "",
                "form-0-email": "test@test.test",
                "form-0-first_name": "Sarah",
                "form-0-last_name": "Lambda",
                "form-0-profession": "organisateurice",
                "form-0-organisation": f"{self.referent.organisation.pk}",
                "form-0-conseiller_numerique": "False",
                "form-1-id": "",
                "form-1-email": "test2@test.test",
                "form-1-first_name": "Abdel",
                "form-1-last_name": "Sigma",
                "form-1-profession": "organisateurice",
                "form-1-organisation": f"{self.referent.organisation.pk}",
                "form-1-conseiller_numerique": "False",
            },
            form.data,
        )
        # Checking data is consistent between form and subforms
        self.assertEqual(form.data, form.forms[0].data)
        self.assertEqual(form.data, form.forms[1].data)
        self.assertEqual(
            form.cleaned_data,
            [
                {
                    "conseiller_numerique": False,
                    "email": "test@test.test",
                    "first_name": "Sarah",
                    "id": None,
                    "last_name": "Lambda",
                    "organisation": self.referent.organisation,
                    "profession": "organisateurice",
                },
                {
                    "conseiller_numerique": False,
                    "email": "test2@test.test",
                    "first_name": "Abdel",
                    "id": None,
                    "last_name": "Sigma",
                    "organisation": self.referent.organisation,
                    "profession": "organisateurice",
                },
            ],
        )
        self.assertEqual(form.add_prefix(1), form.forms[1].prefix)
        # Check previous left_form was deleted to host another form data
        self.assertRaises(AttributeError, getattr, form.left_form, "cleaned_data")

    def test_is_valid_duplicate_email_is_not_valid(self):
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": "",
            "form-0-email": "test@test.test",
            "form-0-first_name": "Sarah",
            "form-0-last_name": "Lambda",
            "form-0-profession": "organisateurice",
            "form-0-organisation": f"{self.referent.organisation.pk}",
            "form-0-conseiller_numerique": "False",
            "form-__temp__-id": "",
            "form-__temp__-email": "test@test.test",
            "form-__temp__-first_name": "Abdel",
            "form-__temp__-last_name": "Sigma",
            "form-__temp__-profession": "organisateurice",
            "form-__temp__-organisation": f"{self.referent.organisation.pk}",
            "form-__temp__-conseiller_numerique": "False",
        }

        form = self.form_cls(
            force_left_form_check=False,
            form_kwargs={"referent": self.referent},
            data=data,
        )
        self.assertEqual(1, len(form.forms))
        self.assertFalse(form.is_valid())
        self.assertEqual(data, form.data)

        self.assertEqual(1, len(form.forms))
        self.assertEqual(1, len(form.left_form.errors))
