from datetime import datetime, timedelta
from unittest import skip

from django.conf import settings
from django.contrib import messages as django_messages

from django.db.models import Q
from django.test import override_settings, tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from freezegun import freeze_time
from pytz import timezone as pytz_timezone

from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Autorisation, Connection, Journal, Usager
from aidants_connect_web.tests.factories import (
    AidantFactory,
    OrganisationFactory,
    UsagerFactory,
)
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

    def test_well_formatted_form_triggers_redirect_to_FC(self):
        self.client.force_login(self.aidant_thierry)
        data = {"demarche": ["papiers", "logement"], "duree": "SHORT"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "SHORT",
            "is_remote": True,
        }
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)
        data = {"demarche": ["papiers", "logement"], "duree": "LONG"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)
        data = {"demarche": ["papiers", "logement"], "duree": "LONG", "is_remote": True}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)


ETAT_URGENCE_2020_LAST_DAY = datetime.strptime("23/05/2020 +0100", "%d/%m/%Y %z")


@skip(
    "This test used to work during the COVID-19 lockdown in March 2020 ('duree': 'EUS_03_20' & 'is_remote': 'True')"  # noqa
)
@tag("new_mandat", "confinement")
@override_settings(ETAT_URGENCE_2020_LAST_DAY=ETAT_URGENCE_2020_LAST_DAY)
@freeze_time(datetime(2020, 5, 20, tzinfo=pytz_timezone("Europe/Paris")))
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

    def test_confinement_entries_create_remote_autorisation_and_journal_entries(self):
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
            Q(action="create_autorisation") | Q(action="create_attestation")
        )

        status_journal_entry = list(
            journal_entries.values_list("is_remote_mandat", flat=True)
        )
        self.assertEqual(status_journal_entry.count(True), 3)

        autorisation_journal_entry = journal_entries.last()
        self.assertEqual(autorisation_journal_entry.duree, 3)

        # test autorisations
        autorisations = Autorisation.objects.all()
        remote_statuses = [auto.mandat.is_remote for auto in autorisations]
        self.assertEqual(remote_statuses, [True, True])
        expiration_dates = [auto.mandat.expiration_date for auto in autorisations]
        self.assertEqual(
            expiration_dates, [ETAT_URGENCE_2020_LAST_DAY, ETAT_URGENCE_2020_LAST_DAY]
        )


@tag("new_mandat")
class NewMandatRecapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organisation = OrganisationFactory()
        self.aidant_thierry = AidantFactory(organisation=self.organisation)
        device = self.aidant_thierry.staticdevice_set.create(id=1)
        device.token_set.create(token="123456")
        device.token_set.create(token="223456")
        self.aidant_monique = AidantFactory(
            first_name="Monique",
            username="monique@monique.com",
            organisation=self.organisation,
        )
        device = self.aidant_monique.staticdevice_set.create(id=2)
        device.token_set.create(token="323456")
        self.organisation_nantes = OrganisationFactory(name="Association Aide'o'Web")
        self.aidant_marge = AidantFactory(
            first_name="Marge", username="Marge", organisation=self.organisation_nantes
        )
        device = self.aidant_marge.staticdevice_set.create(id=3)
        device.token_set.create(token="423456")
        self.test_usager_sub = (
            "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1"
        )
        self.test_usager = UsagerFactory(
            given_name="Fabrice", birthplace="95277", sub=self.test_usager_sub,
        )

    def test_recap_url_triggers_the_recap_view(self):
        found = resolve("/creation_mandat/recapitulatif/")
        self.assertEqual(found.func, new_mandat.new_mandat_recap)

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

            last_usager_organisation_papiers_autorisations = Autorisation.objects.filter(  # noqa
                demarche="papiers",
                mandat__usager=self.test_usager,
                mandat__organisation=self.aidant_thierry.organisation,
            ).order_by(
                "-mandat__creation_date"
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
    def setUp(self):
        self.aidant_thierry = AidantFactory()
        self.client = Client()

        self.test_usager = UsagerFactory(
            given_name="Fabrice",
            family_name="MERCIER",
            sub="46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )
        self.autorisation_form = MandatForm(
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

    def test_autorisation_qrcode_url_triggers_the_correct_view(self):
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
