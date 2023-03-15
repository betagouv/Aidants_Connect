import re
from datetime import date, datetime, timedelta
from textwrap import dedent
from typing import List
from unittest import mock
from unittest.mock import ANY, MagicMock, Mock
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages as django_messages
from django.db import transaction
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils import formats, timezone

from freezegun import freeze_time

from aidants_connect_pico_cms.models import MandateTranslation
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    Connection,
    Journal,
    Mandat,
    Usager,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ConnectionFactory,
    MandatFactory,
    OrganisationFactory,
    UsagerFactory,
)
from aidants_connect_web.views import mandat
from aidants_connect_web.views.mandat import RemoteMandateMixin
from aidants_connect_web.views.service import humanize_demarche_names

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL

UUID = "7ce05928-979c-49ab-8e10-a1a221d39acb"


@tag("new_mandat")
class TestRemoteMandateMixin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.phone_number = "0 800 840 800"
        cls.aidant_thierry = AidantFactory()

    def test_process_consent_returns_none_if_not_remote_or_not_blocked_method(self):
        target = RemoteMandateMixin()

        form = self._get_form(["papiers", "logement"])

        for method in RemoteConsentMethodChoices.blocked_methods():
            setattr(target, f"_process_{method}_method", MagicMock())

        result = target.process_consent(
            self.aidant_thierry, self.aidant_thierry.organisation, form
        )

        for method in RemoteConsentMethodChoices.blocked_methods():
            getattr(target, f"_process_{method}_method").assert_not_called()

        self.assertIs(None, result)

        form = self._get_form(
            ["papiers", "logement"], RemoteConsentMethodChoices.LEGACY
        )

        for method in RemoteConsentMethodChoices.blocked_methods():
            setattr(target, f"_process_{method}_method", MagicMock())

        result = target.process_consent(
            self.aidant_thierry, self.aidant_thierry.organisation, form
        )

        for method in RemoteConsentMethodChoices.blocked_methods():
            getattr(target, f"_process_{method}_method").assert_not_called()

        self.assertIs(None, result)

    @mock.patch("aidants_connect_web.views.mandat.uuid4")
    @mock.patch("aidants_connect_common.utils.sms_api.SmsApiMock.send_sms")
    def test_process_sms_template(self, send_sms_mock: Mock, uuid4_mock: Mock):
        uuid4_mock.return_value = UUID

        form = self._get_form(
            list(settings.DEMARCHES.keys()), RemoteConsentMethodChoices.SMS
        )

        RemoteMandateMixin().process_consent(
            self.aidant_thierry, self.aidant_thierry.organisation, form
        )

        send_sms_mock.assert_called_once_with(
            ANY,
            UUID,
            self._trim_margin(
                """Aidant Connect, bonjour.
                |
                |L'organisation COMMUNE D'HOULBEC COCHEREL souhaite créer un mandat\
                | pour une durée d'un mois (31 jours) en votre nom pour les démarches\
                | suivantes :
                |
                |- Argent,
                |- Étranger,
                |- Famille,
                |- Justice,
                |- Logement,
                |- Loisirs,
                |- Papiers - citoyenneté,
                |- Social - santé,
                |- Transports,
                |- Travail.
                |
                |Répondez « Oui » pour accepter le mandat."""
            ),
        )

        send_sms_mock.reset_mock()

        with transaction.atomic():
            Journal.objects.filter(consent_request_id=UUID).delete()

        form = self._get_form(["papiers"], RemoteConsentMethodChoices.SMS)

        RemoteMandateMixin().process_consent(
            self.aidant_thierry, self.aidant_thierry.organisation, form
        )

        send_sms_mock.assert_called_once_with(
            ANY,
            UUID,
            self._trim_margin(
                """Aidant Connect, bonjour.
                |
                |L'organisation COMMUNE D'HOULBEC COCHEREL souhaite\
                | créer un mandat pour une durée d'un mois (31 jours) en votre nom pour\
                | la démarche Papiers - citoyenneté.
                |
                |Répondez « Oui » pour accepter le mandat."""
            ),
        )

    def _trim_margin(self, message):
        return re.sub(r"[\r\t\f\v  ]+\|", "", message, flags=re.MULTILINE)

    def _get_form(
        self,
        demarche: List[str],
        remote_constent_method: RemoteConsentMethodChoices | None = None,
    ):
        data = {
            "demarche": demarche,
            "duree": "MONTH",
            "is_remote": remote_constent_method is not None,
            "user_phone": self.phone_number,
        }

        if remote_constent_method:
            data["remote_constent_method"] = remote_constent_method.value

        form = MandatForm(data=data)

        if not form.is_valid():
            self.fail(
                f"Test form is invalid because of the following errors: {form.errors}"
            )

        return form


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
        self.assertEqual(found.func.view_class, mandat.NewMandat)

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

        # When mandate is remote and consent method is absent,
        # mandate creation should fail
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "SHORT",
            "is_remote": True,
        }
        response = self.client.post("/creation_mandat/", data=data)
        self.assertEqual(response.status_code, 200)

        # When mandate is remote and consent method is legacy,
        # mandate creation should succeed
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "SHORT",
            "is_remote": True,
            "remote_constent_method": RemoteConsentMethodChoices.LEGACY.name,
        }
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)

        # When mandate is remote and consent method is SMS and phone number is absent,
        # mandate creation should fail
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "SHORT",
            "is_remote": True,
            "remote_constent_method": RemoteConsentMethodChoices.SMS.name,
        }
        response = self.client.post("/creation_mandat/", data=data)
        self.assertEqual(response.status_code, 200)

        data["user_phone"] = self.phone_number
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/creation_mandat/attente_consentement/")

        data = {"demarche": ["papiers", "logement"], "duree": "LONG"}
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)
        data = {
            "demarche": ["papiers", "logement"],
            "duree": "LONG",
            "is_remote": True,
            "remote_constent_method": RemoteConsentMethodChoices.SMS.name,
            "user_phone": self.phone_number,
        }
        response = self.client.post("/creation_mandat/", data=data)
        self.assertRedirects(
            response,
            "/creation_mandat/attente_consentement/",
        )


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
        self.assertEqual(found.func.view_class, mandat.NewMandatRecap)

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
                Autorisation.objects.filter(
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

    def test_autorisation_qrcode_url_triggers_the_correct_view(self):
        found = resolve("/creation_mandat/qrcode/")
        self.assertEqual(found.func, mandat.attestation_qrcode)

    def test_new_mandat_waiting_room_url_triggers_the_correct_view(self):
        found = resolve(reverse("new_mandat_waiting_room"))
        self.assertEqual(found.func.view_class, mandat.WaitingRoom)

    def test_new_mandat_waiting_room_json_url_triggers_the_correct_view(self):
        found = resolve(reverse("new_mandat_waiting_room_json"))
        self.assertEqual(found.func.view_class, mandat.WaitingRoomJson)

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

    @freeze_time(datetime(2020, 7, 18, 3, 20, 34, 0, tzinfo=ZoneInfo("Europe/Paris")))
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


class TestClearConnectionView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory()
        cls.client = Client()

        cls.test_usager = UsagerFactory(
            given_name="Fabrice",
            family_name="MERCIER",
            sub="46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )

    def test_clear_session_and_redirect(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = 1
        session["qr_code_mandat_id"] = 2
        session.save()

        self.assertEqual(1, self.client.session["connection"])
        self.assertEqual(2, self.client.session["qr_code_mandat_id"])

        parameter = urlencode(
            {"next": reverse("renew_mandat", kwargs={"usager_id": self.test_usager.id})}
        )
        response = self.client.get(f"{reverse('clear_connection')}?{parameter}")
        self.assertEqual(302, response.status_code)
        self.assertEqual(f"/renew_mandat/{self.test_usager.id}", response.url)

        self.assertIsNone(self.client.session.get("connection"))
        self.assertIsNone(self.client.session.get("qr_code_mandat_id"))


class TranslationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry: Aidant = AidantFactory()
        cls.lang: MandateTranslation = MandateTranslation.objects.create(
            lang="pus", body="# Test title\n\nTest"
        )

    def test_get_triggers_the_correct_view(self):
        found = resolve(reverse("mandate_translation"))
        self.assertEqual(found.func.view_class, mandat.Translation)

    def test_get_renders_the_correct_template(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.get(reverse("mandate_translation"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/attestation_translation.html"
        )

    def test_post_returns_404_on_unknown_lang(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.post(
            reverse("mandate_translation"), data={"lang_code": "aaaaaaaaaaaaa"}
        )

        self.assertEqual(404, response.status_code)

    def test_post_returns_html_translation_on_known_lang(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.post(
            reverse("mandate_translation"), data={"lang_code": self.lang.lang}
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(b"<h1>Test title</h1>\n<p>Test</p>", response.content)


class AttestationVisualisationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_1: Aidant = AidantFactory()
        cls.aidant_2: Aidant = AidantFactory()
        cls.mandat: Mandat = MandatFactory(organisation=cls.aidant_1.organisation)
        cls.mandat_no_template: Mandat = MandatFactory(
            organisation=cls.aidant_1.organisation, template_path=None
        )
        cls.mandat_aidant_2: Mandat = MandatFactory(
            organisation=cls.aidant_2.organisation, template_path=None
        )

    def test_get_triggers_the_correct_view(self):
        found = resolve(
            reverse("mandat_visualisation", kwargs={"mandat_id": self.mandat.pk})
        )
        self.assertEqual(found.func.view_class, mandat.AttestationVisualisation)

    def test_raises_404_on_mandate_not_found(self):
        self.client.force_login(self.aidant_1)

        response = self.client.get(
            reverse("mandat_visualisation", kwargs={"mandat_id": 10_000_000})
        )

        self.assertEqual(response.status_code, 404)

    def test_raises_404_on_mandate_found_for_another_organisation(self):
        self.client.force_login(self.aidant_1)

        response = self.client.get(
            reverse(
                "mandat_visualisation", kwargs={"mandat_id": self.mandat_aidant_2.pk}
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_variables_set_for_mandate_with_template(self):
        """
        Should set ``modified=False`` in ``request.context`` and
        set ``qr_code_mandat_id`` in ``request.session``
        """
        self.client.force_login(self.aidant_1)

        response = self.client.get(
            reverse("mandat_visualisation", kwargs={"mandat_id": self.mandat.pk})
        )

        self.assertEqual(
            self.mandat.pk,
            response.context["request"].session.get("qr_code_mandat_id"),
            "'qr_code_mandat_id' should not be set to the mandate ID in "
            "request.session when the mandate has a template path set",
        )

        self.assertFalse(
            response.context["modified"],
            "'modified' should be set to False in context when the mandate has "
            "a template path set",
        )

    def test_variables_set_for_mandate_without_template(self):
        """
        Should set ``modified=True`` in ``request.context`` and
        not set ``qr_code_mandat_id`` in ``request.session``
        """
        self.client.force_login(self.aidant_1)

        response = self.client.get(
            reverse(
                "mandat_visualisation", kwargs={"mandat_id": self.mandat_no_template.pk}
            )
        )

        self.assertIsNone(
            response.context["request"].session.get("qr_code_mandat_id"),
            "'qr_code_mandat_id' should not be set in request.session when the mandate "
            "deosn't have a template path set",
        )

        self.assertTrue(
            response.context["modified"],
            "'modified' should be set to True in context when the mandate doesn't "
            "have a template path set",
        )

    def test_get_renders_the_template_on_mandate_found(self):
        self.client.force_login(self.aidant_1)

        response = self.client.get(
            reverse("mandat_visualisation", kwargs={"mandat_id": self.mandat.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/attestation.html")

        expected_context = {
            "usager": self.mandat.usager,
            "aidant": self.aidant_1,
            "date": formats.date_format(self.mandat.creation_date.date(), "l j F Y"),
            "demarches": [
                humanize_demarche_names(it.demarche)
                for it in self.mandat.autorisations.all()
            ],
            "duree": self.mandat.get_duree_keyword_display(),
            "current_mandat_template": self.mandat.get_mandate_template_path(),
            "final": True,
            "modified": False,
        }

        for key, expected in expected_context.items():
            self.assertEqual(
                expected,
                response.context[key],
                dedent(
                    f"""
                    Context for variable {key!r} is different from expected
                    expected: {expected}
                    got: {response.context[key]}"""
                ),
            )


class AttestationProjectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.connection: Connection = ConnectionFactory(
            duree_keyword="SHORT", demarches=["argent", "papiers"]
        )
        cls.aidant_1: Aidant = AidantFactory()

    def test_get_triggers_the_correct_view(self):
        found = resolve(reverse("new_attestation_projet"))
        self.assertEqual(found.func.view_class, mandat.AttestationProject)

    def test_logout_on_no_connection(self):
        self.client.force_login(self.aidant_1)

        session = self.client.session
        session["connection"] = 10_000_000
        session.save()

        self.assertTrue(self.aidant_1.is_authenticated)

        response = self.client.get(reverse("new_attestation_projet"))

        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.status_code, 403)

    @freeze_time("2020-01-01 07:00:00")
    def test_renders_attestation(self):
        self.client.force_login(self.aidant_1)

        session = self.client.session
        session["connection"] = self.connection.pk
        session.save()

        response = self.client.get(reverse("new_attestation_projet"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/attestation.html")

        expected_context = {
            "usager": self.connection.usager,
            "aidant": self.aidant_1,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(it) for it in ["argent", "papiers"]],
            "duree": "pour une durée de 1 jour",
            "current_mandat_template": settings.MANDAT_TEMPLATE_PATH,
            "final": False,
            "modified": False,
        }

        for key, expected in expected_context.items():
            self.assertEqual(
                expected,
                response.context[key],
                dedent(
                    f"""
                    Context for variable {key!r} is different from expected
                    expected: {expected}
                    got: {response.context[key]}"""
                ),
            )


class AttestationFinalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.connection: Connection = ConnectionFactory(
            duree_keyword="SHORT", demarches=["argent", "papiers"]
        )
        cls.aidant_1: Aidant = AidantFactory()

    def test_get_triggers_the_correct_view(self):
        found = resolve(reverse("new_attestation_final"))
        self.assertEqual(found.func.view_class, mandat.AttestationFinal)

    def test_logout_on_no_connection(self):
        self.client.force_login(self.aidant_1)

        session = self.client.session
        session["connection"] = 10_000_000
        session.save()

        self.assertTrue(self.aidant_1.is_authenticated)

        response = self.client.get(reverse("new_attestation_final"))

        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.status_code, 403)

    @freeze_time("2020-01-01 07:00:00")
    def test_renders_attestation(self):
        self.client.force_login(self.aidant_1)

        session = self.client.session
        session["connection"] = self.connection.pk
        session.save()

        response = self.client.get(reverse("new_attestation_final"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/attestation.html")

        expected_context = {
            "usager": self.connection.usager,
            "aidant": self.aidant_1,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(it) for it in ["argent", "papiers"]],
            "duree": "pour une durée de 1 jour",
            "current_mandat_template": settings.MANDAT_TEMPLATE_PATH,
            "final": True,
            "modified": False,
        }

        for key, expected in expected_context.items():
            self.assertEqual(
                expected,
                response.context[key],
                dedent(
                    f"""
                    Context for variable {key!r} is different from expected
                    expected: {expected}
                    got: {response.context[key]}"""
                ),
            )
