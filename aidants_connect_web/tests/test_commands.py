from datetime import datetime, timedelta, timezone

from django.core.management import call_command
from django.test import tag, TestCase

from freezegun import freeze_time

from aidants_connect_web.models import Connection
from aidants_connect_web.tests.factories import ConnectionFactory


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
