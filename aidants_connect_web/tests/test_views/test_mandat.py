from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages as django_messages
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from freezegun import freeze_time
from pytz import timezone as pytz_timezone

from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Autorisation, Connection, Journal, Usager
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    OrganisationFactory,
    UsagerFactory,
)
from aidants_connect_web.views import mandat

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("new_mandat")
@override_settings(PHONENUMBER_DEFAULT_REGION="FR")
class NewMandatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.phone_number = "0 800 840 800"
        cls.aidant_thierry = AidantFactory()
        cls.aidant_nour = AidantFactory()
        cls.aidant_nour.organisations.set(
            [cls.aidant_nour.organisation, cls.aidant_thierry.organisation]
        )

    def test_new_mandat_url_triggers_new_mandat_view(self):
        found = resolve("/creation_mandat/")
        self.assertEqual(found.func, mandat.new_mandat)

    def test_new_mandat_url_triggers_new_mandat_template(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_no_warning_displayed_for_single_structure_aidant(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertNotContains(
            response, "Attention, vous allez créer un mandat au nom de cette structure"
        )

    def test_warning_displayed_for_multi_structure_aidant(self):
        self.client.force_login(self.aidant_nour)
        response = self.client.get("/creation_mandat/")
        self.assertContains(
            response, "Attention, vous allez créer un mandat au nom de cette structure"
        )

    def test_badly_formatted_form_triggers_original_template(self):
        self.client.force_login(self.aidant_thierry)
        data = {"demarche": ["papiers", "logement"], "duree": "RAMDAM"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_well_formatted_form_triggers_redirect_to_FC(self):
        self.client.force_login(self.aidant_thierry)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)

        # When mandate is remot and telephone number is absent,
        # mandate creation should fail
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "SHORT",
            "is_remote": True,
        }
        response = self.client.post("/creation_mandat/", data=data)
        # TODO: Reactivate when SMS consent is a thing
        # self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302)

        data["user_phone"] = self.phone_number
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)

        data = {"demarche": ["papiers", "logement"], "duree": "LONG"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "LONG",
            "is_remote": True,
            "user_phone": self.phone_number,
        }
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)


@tag("new_mandat")
class NewMandatRecapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.organisation = OrganisationFactory()
        cls.aidant_thierry = AidantFactory(organisation=cls.organisation)
        device = cls.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="223456")
        cls.aidant_monique = AidantFactory(
            first_name="Monique",
            username="monique@monique.com",
            organisation=cls.organisation,
        )
        device = cls.aidant_monique.staticdevice_set.create(id=2)
        device.token_set.create(token="323456")
        cls.organisation_nantes = OrganisationFactory(name="Association Aide'o'Web")
        cls.aidant_marge = AidantFactory(
            first_name="Marge", username="Marge", organisation=cls.organisation_nantes
        )
        device = cls.aidant_marge.staticdevice_set.create(id=3)
        device.token_set.create(token="423456")
        cls.test_usager_sub = (
            "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1"
        )
        cls.test_usager = UsagerFactory(
            given_name="Fabrice",
            birthplace="95277",
            sub=cls.test_usager_sub,
        )

    def test_recap_url_triggers_the_recap_view(self):
        found = resolve("/creation_mandat/recapitulatif/")
        self.assertEqual(found.func, mandat.new_mandat_recap)

    def test_recap_url_triggers_the_recap_template(self):
        self.client.force_login(self.aidant_thierry)
        mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
            usager=self.test_usager,
        )
        session = self.client.session
        session["connection"] = mandat_builder.id
        session.save()

        response = self.client.get("/creation_mandat/recapitulatif/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat_recap.html"
        )

    def test_post_to_recap_with_correct_data_redirects_to_success(self):
        self.client.force_login(self.aidant_thierry)
        mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
            usager=self.test_usager,
        )
        session = self.client.session
        session["connection"] = mandat_builder.id
        session.save()

        response = self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )
        self.assertEqual(Usager.objects.all().count(), 1)
        self.assertRedirects(response, "/creation_mandat/succes/")

        last_journal_entries = Journal.objects.all().order_by("-creation_date")

        self.assertEqual(last_journal_entries.count(), 4)
        self.assertEqual(last_journal_entries[0].action, "create_autorisation")
        self.assertEqual(last_journal_entries[0].demarche, "papiers")
        self.assertEqual(last_journal_entries[1].action, "create_autorisation")
        self.assertEqual(last_journal_entries[1].demarche, "logement")
        self.assertEqual(last_journal_entries[2].action, "create_attestation")
        self.assertEqual(last_journal_entries[2].demarche, "logement,papiers")

    def test_post_to_recap_without_usager_creates_error(self):
        self.client.force_login(self.aidant_thierry)
        mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder.id
        session.save()

        response = self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)

    def test_updating_autorisation_for_same_organisation(self):
        # first session : creating the autorisation
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()

        # trigger the mandat creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        self.assertEqual(Autorisation.objects.count(), 1)
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_autorisation")

        # second session : 'updating' the autorisation
        mandat_builder_2 = Connection.objects.create(
            usager=self.test_usager,
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
        )
        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()

        # trigger the mandat creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "223456"},
        )

        self.assertEqual(Autorisation.objects.count(), 3)

        last_usager_organisation_papiers_autorisations = Autorisation.objects.filter(
            demarche="papiers",
            mandat__usager=self.test_usager,
            mandat__organisation=self.aidant_thierry.organisation,
        ).order_by("-mandat__creation_date")
        new_papiers_autorisation = last_usager_organisation_papiers_autorisations[0]
        old_papiers_autorisation = last_usager_organisation_papiers_autorisations[1]
        self.assertEqual(new_papiers_autorisation.duration_for_humans, 365)
        self.assertTrue(old_papiers_autorisation.is_revoked)

        last_journal_entries = Journal.objects.all().order_by("-creation_date")
        self.assertEqual(last_journal_entries[0].action, "create_autorisation")
        self.assertEqual(last_journal_entries[0].demarche, "papiers")
        self.assertEqual(last_journal_entries[1].action, "cancel_autorisation")
        self.assertEqual(last_journal_entries[2].action, "create_autorisation")
        self.assertEqual(last_journal_entries[2].demarche, "logement")

        self.assertEqual(
            len(self.aidant_thierry.get_active_demarches_for_usager(self.test_usager)),
            2,
        )

    def test_updating_expired_autorisation_for_same_organisation(self):
        # first session : creating the autorisation
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()

        # trigger the mandat creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        self.assertEqual(Autorisation.objects.count(), 1)
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_autorisation")

        with freeze_time(timezone.now() + +timedelta(days=6)):
            # second session : 'updating' the autorisation
            self.client.force_login(self.aidant_thierry)
            mandat_builder_2 = Connection.objects.create(
                usager=self.test_usager,
                demarches=["papiers", "logement"],
                duree_keyword="LONG",
            )
            session = self.client.session
            session["connection"] = mandat_builder_2.id
            session.save()

            # trigger the mandat creation
            self.client.post(
                "/creation_mandat/recapitulatif/",
                data={"personal_data": True, "brief": True, "otp_token": "223456"},
            )

            self.assertEqual(Autorisation.objects.count(), 3)

            last_usager_organisation_papiers_autorisations = (
                Autorisation.objects.filter(  # noqa
                    demarche="papiers",
                    mandat__usager=self.test_usager,
                    mandat__organisation=self.aidant_thierry.organisation,
                ).order_by("-mandat__creation_date")
            )
            new_papiers_autorisation = last_usager_organisation_papiers_autorisations[0]
            old_papiers_autorisation = last_usager_organisation_papiers_autorisations[1]
            self.assertEqual(new_papiers_autorisation.duration_for_humans, 366)  # noqa
            self.assertTrue(old_papiers_autorisation.is_expired)
            self.assertFalse(old_papiers_autorisation.is_revoked)

            last_journal_entries = Journal.objects.all().order_by("-id")
            self.assertEqual(last_journal_entries[0].action, "create_autorisation")
            self.assertEqual(last_journal_entries[0].demarche, "papiers")
            self.assertEqual(last_journal_entries[1].action, "create_autorisation")
            self.assertEqual(last_journal_entries[1].demarche, "logement")
            self.assertEqual(last_journal_entries[2].action, "create_attestation")
            self.assertEqual(last_journal_entries[2].demarche, "logement,papiers")
            self.assertNotIn(
                "cancel_autorisation",
                [journal_entry.action for journal_entry in last_journal_entries],
            )

            self.assertEqual(
                len(
                    self.aidant_thierry.get_active_demarches_for_usager(
                        self.test_usager
                    )
                ),
                2,
            )

    @override_settings(OTP_STATIC_THROTTLE_FACTOR=0)  # to prevent throttling
    def test_updating_revoked_autorisation_for_same_organisation(self):
        # first session : creating the autorisation
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()

        # trigger the mandat creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        self.assertEqual(Autorisation.objects.count(), 1)
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_autorisation")

        # revoke
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        last_autorisation = Autorisation.objects.last()
        last_autorisation.revoke(
            aidant=self.aidant_thierry, revocation_date=timezone.now()
        )

        # second session : 'updating' the autorisation
        self.client.force_login(self.aidant_thierry)
        mandat_builder_2 = Connection.objects.create(
            usager=self.test_usager,
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
        )
        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()

        # trigger the mandat creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "223456"},
        )

        self.assertEqual(Autorisation.objects.count(), 3)

        last_usager_organisation_papiers_autorisations = Autorisation.objects.filter(
            demarche="papiers",
            mandat__usager=self.test_usager,
            mandat__organisation=self.aidant_thierry.organisation,
        ).order_by("-mandat__creation_date")
        new_papiers_autorisation = last_usager_organisation_papiers_autorisations[0]
        old_papiers_autorisation = last_usager_organisation_papiers_autorisations[1]
        self.assertEqual(new_papiers_autorisation.duration_for_humans, 365)
        self.assertFalse(old_papiers_autorisation.is_expired)
        self.assertTrue(old_papiers_autorisation.is_revoked)

        last_journal_entries = Journal.objects.all().order_by("-id")
        self.assertEqual(last_journal_entries[0].action, "create_autorisation")
        self.assertEqual(last_journal_entries[0].demarche, "papiers")
        self.assertEqual(last_journal_entries[1].action, "create_autorisation")
        self.assertEqual(last_journal_entries[1].demarche, "logement")
        self.assertEqual(last_journal_entries[2].action, "create_attestation")
        self.assertEqual(last_journal_entries[2].demarche, "logement,papiers")

        self.assertEqual(
            len(self.aidant_thierry.get_active_demarches_for_usager(self.test_usager)),
            2,
        )

    def test_updating_autorisation_for_different_aidant_of_same_organisation(self):
        # first session : creating the autorisation
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()

        # trigger the autorisation creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )
        self.client.logout()

        # second session : Create same autorisation with other aidant
        self.client.force_login(self.aidant_monique)
        mandat_builder_2 = Connection.objects.create(
            usager=self.test_usager,
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
        )
        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()

        # trigger the autorisation creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "323456"},
        )

        self.assertEqual(Autorisation.objects.count(), 3)

        last_usager_papiers_autorisations = Autorisation.objects.filter(
            demarche="papiers", mandat__usager=self.test_usager
        ).order_by("-mandat__creation_date")
        new_papiers_autorisation = last_usager_papiers_autorisations[0]
        old_papiers_autorisation = last_usager_papiers_autorisations[1]
        self.assertEqual(new_papiers_autorisation.duration_for_humans, 365)
        self.assertTrue(old_papiers_autorisation.is_revoked)

        last_journal_entries = Journal.objects.all().order_by("-creation_date")
        self.assertEqual(last_journal_entries[0].action, "create_autorisation")
        self.assertEqual(last_journal_entries[0].demarche, "papiers")
        self.assertEqual(last_journal_entries[1].action, "cancel_autorisation")
        self.assertEqual(last_journal_entries[2].action, "create_autorisation")
        self.assertEqual(last_journal_entries[2].demarche, "logement")

        self.assertEqual(
            len(self.aidant_thierry.get_active_demarches_for_usager(self.test_usager)),
            2,
        )

    def test_updating_autorisation_for_different_aidant_of_different_organisation(self):
        # first session : creating the autorisation
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()
        # trigger the autorisation creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )
        self.client.logout()

        # second session : Create same autorisation with other aidant
        self.client.force_login(self.aidant_marge)
        mandat_builder_2 = Connection.objects.create(
            usager=self.test_usager,
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
        )
        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()

        # trigger the autorisation creation
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "423456"},
        )

        self.assertEqual(Autorisation.objects.count(), 3)

        last_usager_papiers_autorisations = Autorisation.objects.filter(
            demarche="papiers", mandat__usager=self.test_usager
        ).order_by("-mandat__creation_date")
        new_papiers_autorisation = last_usager_papiers_autorisations[0]
        old_papiers_autorisation = last_usager_papiers_autorisations[1]
        self.assertEqual(new_papiers_autorisation.duration_for_humans, 365)
        self.assertFalse(old_papiers_autorisation.is_revoked)

        last_journal_entries = Journal.objects.all().order_by("-creation_date")
        self.assertEqual(last_journal_entries[0].action, "create_autorisation")
        self.assertEqual(last_journal_entries[0].demarche, "papiers")
        self.assertEqual(last_journal_entries[1].action, "create_autorisation")
        self.assertEqual(last_journal_entries[1].demarche, "logement")
        self.assertNotIn(
            "cancel_autorisation",
            [journal_entry.action for journal_entry in last_journal_entries],
        )

        self.assertEqual(
            len(self.aidant_thierry.get_active_demarches_for_usager(self.test_usager)),
            1,
        )
        self.assertEqual(
            len(self.aidant_marge.get_active_demarches_for_usager(self.test_usager)), 2
        )


@tag("new_mandat")
class GenerateAttestationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory()
        cls.client = Client()

        cls.test_usager = UsagerFactory(
            given_name="Fabrice",
            family_name="MERCIER",
            sub="46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )
        cls.autorisation_form = MandatForm(
            data={"demarche": ["papiers", "logement"], "duree": "short"}
        )

        Connection.objects.create(
            id=1,
            state="test_another_state",
            connection_type="FS",
            nonce="test_another_nonce",
            demarches=["papiers", "logement"],
            duree_keyword="SHORT",
            usager=cls.test_usager,
        )

    def test_attestation_projet_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/visualisation/projet/")
        self.assertEqual(found.func, mandat.attestation_projet)

    def test_attestation_final_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/visualisation/final/")
        self.assertEqual(found.func, mandat.attestation_final)

    def test_autorisation_qrcode_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/qrcode/")
        self.assertEqual(found.func, mandat.attestation_qrcode)

    def test_autorisation_qrcode_ok_with_connection_and_mandat_id(self):
        mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.test_usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )

        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = 1
        session["qr_code_mandat_id"] = mandat.pk
        session.save()

        response = self.client.get("/creation_mandat/qrcode/")
        self.assertEqual(response.status_code, 200)

    def test_autorisation_qrcode_ok_with_mandat_id(self):
        mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.test_usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )

        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["qr_code_mandat_id"] = mandat.pk
        session.save()

        response = self.client.get("/creation_mandat/qrcode/")
        self.assertEqual(response.status_code, 200)

    def test_response_is_the_print_page(self):
        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = 1
        session.save()

        response = self.client.get("/creation_mandat/visualisation/projet/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/attestation.html")

    @freeze_time(
        datetime(2020, 7, 18, 3, 20, 34, 0, tzinfo=pytz_timezone("Europe/Paris"))
    )
    def test_attestation_contains_text(self):
        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = 1
        session.save()

        response = self.client.get("/creation_mandat/visualisation/projet/")
        response_content = response.content.decode("utf-8")

        self.assertIn("mandataire", response_content)
        self.assertIn("Fabrice MERCIER", response_content)
        self.assertIn("Allocation", response_content)
        self.assertIn("1 jour", response_content)
        self.assertIn("HOULBEC COCHEREL", response_content)
        self.assertIn("COMMUNE", response_content)
        # if this fails, check if info is not on second page
        self.assertIn("18 juillet 2020", response_content)
