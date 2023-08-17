import csv
import logging

from django.core.management.base import BaseCommand

from ...constants import HabilitationRequestStatuses
from ...models import HabilitationRequest, Organisation

logger = logging.getLogger()


def import_one_row(row):
    data_pass_id = row[0]
    try:
        orga = Organisation.objects.get(data_pass_id=data_pass_id)
        hab_req, _ = HabilitationRequest.objects.get_or_create(
            email=row[3].lower(),
            organisation=orga,
            defaults={
                "first_name": row[1],
                "last_name": row[2],
            },
        )
        hab_req.status = HabilitationRequestStatuses.STATUS_PROCESSING
        hab_req.save()
    except Exception as e:
        print(e)


class Command(BaseCommand):
    help = "Import last Aidant à former files"

    def add_arguments(self, parser):
        parser.add_argument("aidant_files", nargs="+")

    def handle(self, *args, **options):
        for file in options["aidant_files"]:
            with open(file, newline="") as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=";", quotechar='"')
                next(csv_reader)
                for row in csv_reader:
                    import_one_row(row)
