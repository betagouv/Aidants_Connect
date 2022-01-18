import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command, CommandError
from django.test import tag, TestCase
from freezegun import freeze_time
from django_otp.plugins.otp_static.lib import add_static_token
from django_otp.plugins.otp_static.models import StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_overrides.management.commands.createsuperuser import (
    ERROR_MSG,
    ORGANISATION_ID_ARG,
    ORGANISATION_NAME_ARG,
    ORGANISATION_NAME_ENV,
    ORGANISATION_ID_ENV,
)
from aidants_connect import settings
from aidants_connect_web.models import Connection, Aidant, HabilitationRequest
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    ConnectionFactory,
    HabilitationRequestFactory,
    MandatFactory,
    OrganisationFactory,
)

TZ_PARIS = timezone(offset=timedelta(hours=1), name="Europe/Paris")

# Before the COVID-19 lockdown
DATE_5_FEVRIER_2020 = datetime(2020, 2, 5, 10, 30, tzinfo=TZ_PARIS)
DATE_6_FEVRIER_2020 = datetime(2020, 2, 6, 10, 30, tzinfo=TZ_PARIS)  # + 1 day
DATE_5_FEVRIER_2021 = datetime(2021, 2, 5, 10, 30, tzinfo=TZ_PARIS)  # + 1 year

# During the COVID-19 lockdown
DATE_15_AVRIL_2020 = datetime(2020, 4, 15, 13, 30, tzinfo=TZ_PARIS)
DATE_16_AVRIL_2020 = datetime(2020, 4, 16, 13, 30, tzinfo=TZ_PARIS)  # + 1 day
DATE_15_AVRIL_2021 = datetime(2021, 4, 15, 13, 30, tzinfo=TZ_PARIS)  # + 1 year

# After the COVID-19 lockdown
DATE_25_MAI_2020 = datetime(2020, 5, 25, 16, 30, tzinfo=TZ_PARIS)
DATE_26_MAI_2020 = datetime(2020, 5, 26, 16, 30, tzinfo=TZ_PARIS)  # + 1 day
DATE_25_MAI_2021 = datetime(2021, 5, 25, 16, 30, tzinfo=TZ_PARIS)  # + 1 year

# The planned end date of the state of emergency
ETAT_URGENCE_2020_LAST_DAY = datetime.strptime(
    "10/07/2020 23:59:59 +0100", "%d/%m/%Y %H:%M:%S %z"
)


@tag("commands")
class DeleteExpiredConnectionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.conn_1 = ConnectionFactory(
            expires_on=datetime(2020, 1, 1, 6, 0, 0, tzinfo=timezone.utc)
        )
        cls.conn_2 = ConnectionFactory(
            expires_on=datetime(2020, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        )

    @freeze_time("2020-01-01 07:00:00")
    def test_delete_expired_connections(self):
        self.assertEqual(Connection.objects.count(), 2)

        command_name = "delete_expired_connections"

        call_command(command_name)
        remaining_connections = Connection.objects.all()
        self.assertEqual(remaining_connections.count(), 1)
        self.assertEqual(remaining_connections.first().id, self.conn_2.id)

        call_command(command_name)
        remaining_connections = Connection.objects.all()
        self.assertEqual(remaining_connections.count(), 1)
        self.assertEqual(remaining_connections.first().id, self.conn_2.id)


@tag("commands")
class DeleteDuplicatedAndObsoleteTokensTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.command_name = "delete_duplicated_static_tokens"

    def test_delete_duplicated_tokens_for_aidant(self):
        aidant = AidantFactory()
        for _ in range(5):
            add_static_token(aidant.username, 123456)
        self.assertEqual(StaticToken.objects.count(), 5)
        call_command(self.command_name)
        self.assertEqual(StaticToken.objects.count(), 1)

    def test_keep_one_token_of_every_value_for_aidant(self):
        aidant = AidantFactory()
        for _ in range(5):
            add_static_token(aidant.username, 123456)
            add_static_token(aidant.username, 789123)
        self.assertEqual(StaticToken.objects.count(), 10)
        call_command(self.command_name)
        self.assertEqual(StaticToken.objects.count(), 2)

    def test_delete_static_device_for_confirmed_simple_aidants(self):
        aidants = [
            AidantFactory(),
            AidantFactory(is_staff=True),
            AidantFactory(is_staff=True, is_superuser=True),
        ]
        for aidant in aidants:
            add_static_token(aidant.username, 123456)
            TOTPDevice(user=aidant, confirmed=True).save()

        self.assertEqual(StaticToken.objects.count(), 3)
        self.assertEqual(TOTPDevice.objects.count(), 3)

        call_command(self.command_name)

        # only the first aidant's static device was deleted
        self.assertEqual(StaticToken.objects.count(), 2)


@tag("commands")
class CreateSuperUserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga_1 = OrganisationFactory()

    def test_raise_error_noinput_orga_id_and_orga_name(self):
        with self.assertRaises(CommandError) as err:
            call_command(
                "createsuperuser",
                f"{ORGANISATION_ID_ARG}={self.orga_1.id}",
                f'{ORGANISATION_NAME_ARG}="L\'Internationale des travailleurs"',
            )

        self.assertEqual(
            err.exception.__str__(), f"{ERROR_MSG} but not both at the same time."
        )

    def test_raise_error_noinput_no_orga(self):
        with self.assertRaises(CommandError) as err:
            call_command("createsuperuser", interactive=False)

        self.assertEqual(err.exception.__str__(), f"{ERROR_MSG}.")

    def test_organisation_name(self):
        def input_mock(*_):
            return "Proletaires_de_tous_les_pays"

        with patch("getpass.getpass", input_mock):
            call_command(
                "createsuperuser",
                f"{ORGANISATION_NAME_ARG}=L'Internationale des travailleurs",
                username="Karl_Marx",
                email="karl_marx@internationale.de",
                stdin={"isatty": True},
            )

            self.assertEqual(
                Aidant.objects.get(username="Karl_Marx").organisation.name,
                "L'Internationale des travailleurs",
            )

    def test_organisation_name_env_var(self):
        def input_mock(*_):
            return "Proletaires_de_tous_les_pays"

        with patch("getpass.getpass", input_mock), patch.dict(
            os.environ, {ORGANISATION_NAME_ENV: "L'Internationale des travailleurs"}
        ):
            call_command(
                "createsuperuser",
                username="Karl_Marx",
                email="karl_marx@internationale.de",
                stdin={"isatty": True},
            )

            self.assertEqual(
                Aidant.objects.get(username="Karl_Marx").organisation.name,
                "L'Internationale des travailleurs",
            )

    def test_organisation_id(self):
        def input_mock(*_):
            return "Proletaires_de_tous_les_pays"

        with patch("getpass.getpass", input_mock):
            call_command(
                "createsuperuser",
                f"{ORGANISATION_ID_ARG}={self.orga_1.pk}",
                username="Karl_Marx",
                email="karl_marx@internationale.de",
                stdin={"isatty": True},
            )

            self.assertEqual(
                Aidant.objects.get(username="Karl_Marx").organisation.name,
                self.orga_1.name,
            )

    def test_organisation_id_non_interactive(self):
        with patch.dict(os.environ, {ORGANISATION_ID_ENV: str(self.orga_1.pk)}):
            call_command(
                "createsuperuser",
                username="Karl_Marx",
                email="karl_marx@internationale.de",
                interactive=False,
            )

            self.assertEqual(
                Aidant.objects.get(username="Karl_Marx").organisation.name,
                self.orga_1.name,
            )

    def test_organisation_id_env_var_non_interactive(self):
        with patch.dict(
            os.environ,
            {
                ORGANISATION_ID_ENV: str(self.orga_1.pk),
                "DJANGO_SUPERUSER_PASSWORD": "Proletaires_de_tous_les_pays",
            },
        ):
            call_command(
                "createsuperuser",
                username="Karl_Marx",
                email="karl_marx@internationale.de",
                interactive=False,
            )

            self.assertEqual(
                Aidant.objects.get(username="Karl_Marx").organisation.name,
                self.orga_1.name,
            )


@tag("commands")
class NewHabilitationRequestsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bizdev = AidantFactory(is_staff=True)

    def three_manual_habilitation_requests_in_three_organisations(self):
        for _ in range(3):
            HabilitationRequestFactory(origin=HabilitationRequest.ORIGIN_RESPONSABLE)
        for _ in range(3):
            HabilitationRequestFactory()

    def four_manual_habilitation_requests_in_two_organisations(self):
        for _ in range(2):
            req_1 = HabilitationRequestFactory(
                origin=HabilitationRequest.ORIGIN_RESPONSABLE
            )
            HabilitationRequestFactory(
                organisation=req_1.organisation,
                origin=HabilitationRequest.ORIGIN_RESPONSABLE,
            )
            HabilitationRequestFactory(organisation=req_1.organisation)

    def test_no_email_is_sent_if_no_habilitation_request(self):
        call_command("notify_new_habilitation_requests")
        self.assertEqual(len(mail.outbox), 0)

    def test_an_email_is_sent_if_there_is_an_habilitation_request(self):
        self.three_manual_habilitation_requests_in_three_organisations()
        call_command("notify_new_habilitation_requests")
        self.assertEqual(len(mail.outbox), 1)
        mail_content = mail.outbox[0].body
        mail_subject = mail.outbox[0].subject
        self.assertIn("3 nouveaux aidants à former", mail_subject)
        self.assertIn("3 nouveaux aidants à former", mail_content)
        self.assertIn("dans 3 structures différentes", mail_content)

    def test_counting_of_habilitation_requests(self):
        self.four_manual_habilitation_requests_in_two_organisations()
        call_command("notify_new_habilitation_requests")
        self.assertEqual(len(mail.outbox), 1)
        mail_content = mail.outbox[0].body
        mail_subject = mail.outbox[0].subject
        self.assertIn("4 nouveaux aidants à former", mail_subject)
        self.assertIn("4 nouveaux aidants à former", mail_content)
        self.assertIn("dans 2 structures différentes", mail_content)


@tag("commands")
class NotifySoonExpiredMandatesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga = OrganisationFactory()
        cls.aidant = AidantFactory(organisation=cls.orga)
        cls.unrelated_aidant = AidantFactory()

    def test_one_soon_expired_mandate(self):
        MandatFactory(organisation=self.orga, duree_keyword="LONG")
        call_command("notify_soon_expired_mandates")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, settings.MANDAT_EXPIRED_SOON_EMAIL_SUBJECT)
        self.assertIn(self.aidant.email, email.recipients())
        self.assertNotIn(self.unrelated_aidant.email, email.recipients())

    def test_two_soon_expired_mandates_in_same_orga(self):
        for _ in range(2):
            MandatFactory(organisation=self.orga, duree_keyword="LONG")
        call_command("notify_soon_expired_mandates")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, settings.MANDAT_EXPIRED_SOON_EMAIL_SUBJECT)
        self.assertIn(self.aidant.email, email.recipients())
        self.assertNotIn(self.unrelated_aidant.email, email.recipients())

    def test_two_soon_expired_mandates_in_different_orgas(self):
        for _ in range(2):
            aidant = AidantFactory()
            MandatFactory(duree_keyword="LONG", organisation=aidant.organisation)
        call_command("notify_soon_expired_mandates")
        self.assertEqual(len(mail.outbox), 2)
        first_email, second_email = mail.outbox
        self.assertNotEqual(first_email.recipients(), second_email.recipients())
        self.assertNotIn(first_email.recipients()[0], second_email.recipients())
        self.assertNotIn(second_email.recipients()[0], first_email.recipients())


@tag("commands")
class NotifyNoTotpWorkersTests(TestCase):
    def test_no_mail_sent_if_no_need(self):
        call_command("notify_no_totp_workers")
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_is_sent_to_the_manager(self):
        aidant = AidantFactory(first_name="Henri", last_name="Tournelle")
        responsable = AidantFactory(
            first_name="Hervé", last_name="Gétal", organisation=aidant.organisation
        )
        responsable.responsable_de.add(aidant.organisation)
        call_command("notify_no_totp_workers")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn(f"{aidant}", message.body)
        self.assertIn("vous-même", message.body)
        self.assertIn(responsable.email, message.recipients())

    def test_aidant_with_carte_totp_does_not_appear_in_email(self):
        responsable = AidantFactory(first_name="Arès", last_name="Ponsable")
        responsable.responsable_de.add(responsable.organisation)
        CarteTOTPFactory(aidant=responsable)
        aidant_with_carte = AidantFactory(
            first_name="Gaetan",
            last_name="Carté",
            organisation=responsable.organisation,
        )
        CarteTOTPFactory(aidant=aidant_with_carte)
        aidant_without_carte = AidantFactory(
            first_name="Roberto",
            last_name="Bogan",
            organisation=responsable.organisation,
        )

        call_command("notify_no_totp_workers")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn(f"{aidant_without_carte}", message.body)
        self.assertNotIn(f"{aidant_with_carte}", message.body)
        self.assertNotIn("vous-même", message.body)
