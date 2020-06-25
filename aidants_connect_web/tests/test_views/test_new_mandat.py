from datetime import datetime

from django.conf import settings
from django.contrib import messages as django_messages
from django.db.models import Q
from django.test import tag, TestCase, override_settings
from django.test.client import Client
from django.urls import resolve

from freezegun import freeze_time
from pytz import timezone

from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Connection, Journal, Mandat, Usager
from aidants_connect_web.tests.factories import AidantFactory, UsagerFactory
from aidants_connect_web.views import new_mandat

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("new_mandat")
class NewMandatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = AidantFactory()

    def test_new_mandat_url_triggers_new_mandat_view(self):
        found = resolve("/creation_mandat/")
        self.assertEqual(found.func, new_mandat.new_mandat)

    def test_new_mandat_url_triggers_new_mandat_template(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/creation_mandat/")
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_badly_formatted_form_triggers_original_template(self):
        self.client.force_login(self.aidant_thierry)
        data = {"demarche": ["papiers", "logement"], "duree": "RAMDAM"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_badly_formatted_form_remote_triggers_original_template(self):
        self.client.force_login(self.aidant_thierry)
        data = {"demarche": ["papiers", "logement"], "duree": "LONG", "is_remote": True}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_well_formatted_form_triggers_redirect_to_FC(self):
        self.client.force_login(self.aidant_thierry)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)


ETAT_URGENCE_2020_LAST_DAY = datetime.strptime("23/05/2020 +0100", "%d/%m/%Y %z")


@tag("new_mandat", "confinement")
@override_settings(ETAT_URGENCE_2020_LAST_DAY=ETAT_URGENCE_2020_LAST_DAY)
@freeze_time(datetime(2020, 5, 20, tzinfo=timezone("Europe/Paris")))
class ConfinementNewMandatRecapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = AidantFactory()
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")

        self.test_usager = UsagerFactory(
            given_name="Fabrice", birthplace="95277", sub="test_sub",
        )
        self.mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"],
            duree_keyword="EUS_03_20",
            mandat_is_remote=True,
            usager=self.test_usager,
        )

    def test_confinement_formatted_form_triggers_redirect_to_FC(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/creation_mandat/",
            data={
                "demarche": ["papiers", "logement"],
                "duree": "EUS_03_20",
                "is_remote": True,
            },
        )
        connection_id = Connection.objects.last().id
        self.assertEqual(self.client.session["connection"], connection_id)
        self.assertEqual(
            Connection.objects.get(id=connection_id).duree_keyword, "EUS_03_20"
        )
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)

    def test_confinement_badly_formatted_form_remote_triggers_original_template(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/creation_mandat/",
            data={
                "demarche": ["papiers", "logement"],
                "duree": "EUS_03_20",
                "is_remote": False,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_confinement_post_to_recap_with_correct_data_redirects_to_success(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session

        session["connection"] = self.mandat_builder.id
        session.save()

        response = self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        self.assertRedirects(response, "/creation_mandat/succes/")

    def test_confinement_entries_create_remote_mandat_and_journal_entries(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session

        session["connection"] = self.mandat_builder.id
        session.save()

        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        # test journal entries
        journal_entries = Journal.objects.filter(
            Q(action="create_mandat") | Q(action="create_attestation")
        )

        status_journal_entry = list(
            journal_entries.values_list("is_remote_mandat", flat=True)
        )
        self.assertEqual(status_journal_entry.count(True), 3)

        mandat_journal_entry = journal_entries.last()
        self.assertEqual(mandat_journal_entry.duree, 3)
        self.assertEqual(
            mandat_journal_entry.additional_information,
            "Mandat conclu à distance "
            "pendant l'état d'urgence sanitaire (23 mars 2020)",
        )

        # test mandats
        mandats = Mandat.objects.all()
        status_mandats = list(mandats.values_list("is_remote_mandat", flat=True))
        self.assertEqual(status_mandats.count(True), 2)
        mandat_2 = Mandat.objects.last()
        self.assertEqual(mandat_2.expiration_date, ETAT_URGENCE_2020_LAST_DAY)


@tag("new_mandat")
class NewMandatRecapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = AidantFactory()
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="223456")
        self.aidant_monique = AidantFactory(username="monique@monique.com")
        device = self.aidant_monique.staticdevice_set.create(id=2)
        device.token_set.create(token="323456")
        self.test_usager_sub = (
            "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1"
        )
        self.test_usager = UsagerFactory(
            given_name="Fabrice", birthplace="95277", sub=self.test_usager_sub,
        )
        self.mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"],
            duree_keyword="LONG",
            usager=self.test_usager,
        )

    def test_recap_url_triggers_the_recap_view(self):
        found = resolve("/creation_mandat/recapitulatif/")
        self.assertEqual(found.func, new_mandat.new_mandat_recap)

    def test_recap_url_triggers_the_recap_template(self):
        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = self.mandat_builder.id
        session.save()

        response = self.client.get("/creation_mandat/recapitulatif/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat_recap.html"
        )

    def test_post_to_recap_with_correct_data_redirects_to_success(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session

        session["connection"] = self.mandat_builder.id
        session.save()

        response = self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )
        self.assertEqual(Usager.objects.all().count(), 1)
        self.assertRedirects(response, "/creation_mandat/succes/")

        last_journal_entries = Journal.objects.all().order_by("-creation_date")

        self.assertEqual(last_journal_entries.count(), 4)
        self.assertEqual(last_journal_entries[0].action, "create_mandat")
        self.assertEqual(last_journal_entries[2].action, "create_attestation")

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

    def test_updating_mandat_for_same_aidant(self):
        # first session : creating the mandat
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()
        # trigger the mandat creation/update
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )

        self.assertEqual(Mandat.objects.count(), 1)
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_mandat")

        # second session : updating the mandat
        mandat_builder_2 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="LONG"
        )

        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()
        # trigger the mandat creation/update
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "223456"},
        )

        self.assertEqual(Mandat.objects.count(), 1)
        updated_mandat = Mandat.objects.get(
            demarche="papiers", usager=self.test_usager, aidant=self.aidant_thierry
        )
        self.assertEqual(updated_mandat.duree_in_days, 365)
        self.assertTrue(
            updated_mandat.creation_date < updated_mandat.last_mandat_renewal_date
        )

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "update_mandat")

    def test_not_updating_mandat_for_different_aidant(self):
        # first session : creating the mandat
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree_keyword="SHORT"
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()
        # trigger the mandat creation/update
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "123456"},
        )
        self.client.logout()

        # second session : Create same mandat with other aidant
        self.client.force_login(self.aidant_monique)
        mandat_builder_2 = Connection.objects.create(
            demarches=["papiers"], duree_keyword="LONG", usager=self.test_usager
        )
        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()

        # trigger the mandat creation/update
        self.client.post(
            "/creation_mandat/recapitulatif/",
            data={"personal_data": True, "brief": True, "otp_token": "323456"},
        )

        self.assertEqual(Mandat.objects.count(), 2)
        first_mandat = Mandat.objects.get(
            demarche="papiers", usager=self.test_usager, aidant=self.aidant_thierry
        )
        self.assertEqual(first_mandat.duree_in_days, 1)

        second_mandat = Mandat.objects.get(
            demarche="papiers", usager=self.test_usager, aidant=self.aidant_monique
        )
        self.assertEqual(second_mandat.duree_in_days, 365)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_mandat")


@tag("new_mandat")
class GenerateMandatPrint(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory()
        self.client = Client()

        self.test_usager = UsagerFactory(
            given_name="Fabrice",
            family_name="MERCIER",
            sub="46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )
        self.mandat_form = MandatForm(
            data={"demarche": ["papiers", "logement"], "duree": "short"}
        )

        Connection.objects.create(
            id=1,
            state="test_another_state",
            connection_type="FS",
            nonce="test_another_nonce",
            demarches=["papiers", "logement"],
            duree_keyword="SHORT",
            usager=self.test_usager,
        )

    def test_attestation_projet_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/visualisation/projet/")
        self.assertEqual(found.func, new_mandat.attestation_projet)

    def test_attestation_final_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/visualisation/final/")
        self.assertEqual(found.func, new_mandat.attestation_final)

    def test_mandat_qrcode_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/qrcode/")
        self.assertEqual(found.func, new_mandat.attestation_qrcode)

    def test_response_is_the_print_page(self):
        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = 1
        session.save()

        response = self.client.get("/creation_mandat/visualisation/projet/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/attestation.html")

    @freeze_time(datetime(2020, 7, 18, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris")))
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
