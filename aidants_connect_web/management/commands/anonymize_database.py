import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from aidants_connect_web.models import Aidant, Journal, Usager


class Command(BaseCommand):

    help = "Remove personal information from the database"

    def handle(self, *args, **options):

        # A little sanity check first.
        if settings.IS_PRODUCTION:
            self.stdout.write(
                "Anonymizing the production database seems like a bad idea."
            )
            sys.exit(1)  # denotes an unsuccessful termination

        self.stdout.write("Anonymizing database...")

        self.stdout.write("  Removing Usagers' personal information...")
        for usager in Usager.objects.order_by("id"):

            uid = usager.id

            self.stdout.write(f"    Usager #{uid}...")

            original_email = usager.email

            usager.given_name = f"UP-{uid}"   # UP = "Usager Prénom"
            usager.family_name = f"UN-{uid}"  # UN = "Usager Nom"
            usager.email = f"u{uid}@usager.fr"
            usager.save()

            for entry in Journal.objects.filter(usager__icontains=original_email):
                entry.usager = usager.full_string_identifier
                entry.save(anonymize=True)

        self.stdout.write("  Removing Aidants' personal information...")
        for aidant in Aidant.objects.exclude(
            email__icontains="beta.gouv.fr"  # keep the staff accounts intact
        ).order_by("id"):

            aid = aidant.id

            self.stdout.write(f"    Aidant #{aid}...")

            original_email = aidant.email

            aidant.first_name = f"AP-{aid}"  # AP = "Aidant Prénom"
            aidant.last_name = f"AN-{aid}"   # AN = "Aidant Nom"
            aidant.email = f"a{aid}@aidant.fr"
            aidant.save()

            for entry in Journal.objects.filter(initiator__icontains=original_email):
                entry.initiator = aidant.full_string_identifier
                entry.save(anonymize=True)

        self.stdout.write("All done.")
