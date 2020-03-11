from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import delete_expired_connections


class Command(BaseCommand):
    help = "Deletes the expired `Connection` objects from the database"

    def handle(self, *args, **options):
        delete_expired_connections()
