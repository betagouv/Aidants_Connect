from datetime import datetime, timezone
from io import StringIO

from django.core.management import call_command
from django.test import tag, TestCase

from freezegun import freeze_time

from aidants_connect_web.models import Connection
from aidants_connect_web.tests.factories import ConnectionFactory


@tag("commands")
class DeleteExpiredConnectionsTest(TestCase):
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

        out = StringIO()
        command_name = "delete_expired_connections"

        call_command(command_name, stdout=out)
        remaining_connections = Connection.objects.all()
        self.assertEqual(remaining_connections.count(), 1)
        self.assertEqual(remaining_connections.first().id, self.conn_2.id)
        self.assertIn("Successfully deleted 1 connection!", out.getvalue())

        call_command(command_name, stdout=out)
        remaining_connections = Connection.objects.all()
        self.assertEqual(remaining_connections.count(), 1)
        self.assertEqual(remaining_connections.first().id, self.conn_2.id)
        self.assertIn("No connection to delete.", out.getvalue())
