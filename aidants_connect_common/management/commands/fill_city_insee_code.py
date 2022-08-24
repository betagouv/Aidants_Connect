import logging

from django.core.management.base import BaseCommand

from aidants_connect_common.tasks import autofill_insee_code

logger = logging.getLogger()


class Command(BaseCommand):
    help = "Fills 'city_insee_code' field in Django models"

    def handle(self, *args, **options):
        autofill_insee_code(logger=logger)
