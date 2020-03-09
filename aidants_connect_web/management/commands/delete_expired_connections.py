from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize

from aidants_connect_web.models import Connection


class Command(BaseCommand):
    help = "Deletes the expired `Connection` objects from the database"

    def handle(self, *args, **options):
        self.stdout.write("Deleting expired connections...")

        expired_connections = Connection.objects.expired()
        deleted_connections_count, _ = expired_connections.delete()

        if deleted_connections_count > 0:
            self.stdout.write(
                f"Successfully deleted {deleted_connections_count} "
                f"connection{pluralize(deleted_connections_count)}!"
            )

        else:
            self.stdout.write("No connection to delete.")
