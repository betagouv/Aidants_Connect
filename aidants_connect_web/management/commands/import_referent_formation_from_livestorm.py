import logging

from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import import_referent_formation_from_livestorm

logger = logging.getLogger()


class Command(BaseCommand):
    help = "Imports person registered to referent formation from Livestorm"

    def handle(self, *args, **options):
        import_referent_formation_from_livestorm(logger=logger)
