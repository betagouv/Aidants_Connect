from unittest import skip

from datetime import datetime, timedelta, timezone

from django.core.management import call_command
from django.test import override_settings, tag, TestCase

from freezegun import freeze_time

from aidants_connect_web.models import (
    Autorisation,
    Connection,
    Mandat,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ConnectionFactory,
    LegacyAutorisationFactory,
    OrganisationFactory,
    UsagerFactory,
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


@skip("This test can only be executed at version 1.0.0-pre.")
@freeze_time("2020-06-30 10:30:00")
@override_settings(ETAT_URGENCE_2020_LAST_DAY=ETAT_URGENCE_2020_LAST_DAY)
class MigrateMandatsTests(TestCase):
    def setUp(self):

        self.orga1 = OrganisationFactory()
        self.orga2 = OrganisationFactory()
        self.orga3 = OrganisationFactory()
        self.orga4 = OrganisationFactory()

        self.aidant1 = AidantFactory(
            organisation=self.orga1,
            email="a1@o1.com",
            username="a1@o1.com",
            password="toto",
        )  # noqa
        self.aidant2 = AidantFactory(
            organisation=self.orga2,
            email="a2@o2.com",
            username="a2@o2.com",
            password="toto",
        )  # noqa
        self.aidant3 = AidantFactory(
            organisation=self.orga3,
            email="a3@o3.com",
            username="a3@o3.com",
            password="toto",
        )  # noqa
        self.aidant4 = AidantFactory(
            organisation=self.orga4,
            email="a4@o4.com",
            username="a4@o4.com",
            password="toto",
        )  # noqa

        self.usager1 = UsagerFactory()
        self.usager2 = UsagerFactory()
        self.usager3 = UsagerFactory()
        self.usager4 = UsagerFactory()

        # `usager1`: 3 `autorisations` for one day, before lockdown
        for demarche in ["papiers", "famille", "social"]:
            LegacyAutorisationFactory(
                usager=self.usager1,
                aidant=self.aidant1,
                creation_date=DATE_5_FEVRIER_2020,
                expiration_date=DATE_6_FEVRIER_2020,
                is_remote=False,
                demarche=demarche,
            )

        # `usager2`: 2 `autorisations` for one day, during lockdown
        for demarche in ["travail", "logement"]:
            LegacyAutorisationFactory(
                usager=self.usager2,
                aidant=self.aidant2,
                creation_date=DATE_15_AVRIL_2020,
                expiration_date=DATE_16_AVRIL_2020,
                is_remote=True,
                demarche=demarche,
            )

        # `usager3`: 2 `autorisations` until the end of lockdown
        for demarche in ["transports", "argent"]:
            LegacyAutorisationFactory(
                usager=self.usager3,
                aidant=self.aidant3,
                creation_date=DATE_15_AVRIL_2020,
                expiration_date=ETAT_URGENCE_2020_LAST_DAY,
                is_remote=True,
                demarche=demarche,
            )

        # `usager4`: 3 `autorisations` for one year, after lockdown
        for demarche in ["justice", "etranger", "loisirs"]:
            LegacyAutorisationFactory(
                usager=self.usager4,
                aidant=self.aidant4,
                creation_date=DATE_25_MAI_2020,
                expiration_date=DATE_25_MAI_2021,
                is_remote=False,
                demarche=demarche,
            )

    def test_migrate_mandats(self):
        self.assertEqual(Autorisation.objects.count(), 10)
        self.assertEqual(Mandat.objects.count(), 0)

        call_command("migrate_mandats")

        mandats = Mandat.objects.order_by("organisation_id")

        self.assertEqual(mandats.count(), 4)
        self.assertEqual(
            [mandat.organisation for mandat in mandats],
            [self.orga1, self.orga2, self.orga3, self.orga4],
        )
        self.assertEqual(
            [mandat.usager for mandat in mandats],
            [self.usager1, self.usager2, self.usager3, self.usager4],
        )
        self.assertEqual(
            [mandat.duree_keyword for mandat in mandats],
            ["SHORT", "SHORT", "EUS_03_20", "LONG"],
        )
        self.assertEqual(
            [mandat.creation_date.strftime("%d/%m/%Y") for mandat in mandats],
            ["05/02/2020", "15/04/2020", "15/04/2020", "25/05/2020"],
        )
        self.assertEqual(
            [
                [auto.id for auto in mandat.autorisations.order_by("pk")]
                for mandat in mandats
            ],  # noqa
            [
                [auto.id for auto in self.usager1.autorisations.order_by("pk")],
                [auto.id for auto in self.usager2.autorisations.order_by("pk")],
                [auto.id for auto in self.usager3.autorisations.order_by("pk")],
                [auto.id for auto in self.usager4.autorisations.order_by("pk")],
            ],
        )


@tag("commands")
class DeleteExpiredConnectionsTests(TestCase):
    def setUp(self):
        self.conn_1 = ConnectionFactory(
            expires_on=datetime(2020, 1, 1, 6, 0, 0, tzinfo=timezone.utc)
        )
        self.conn_2 = ConnectionFactory(
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
