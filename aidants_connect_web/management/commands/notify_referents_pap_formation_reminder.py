from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import notify_referents_pap_formation_reminder


class Command(BaseCommand):
    help = (
        "Reminds referents whose habilitation requests validated for the "
        "pair-à-pair formation are still waiting for account activation "
        "(Pix test not done yet), exactly on the 30th day after the "
        "validation email was sent. Meant to run every day (e.g. as a daily "
        "celery beat periodic task)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the reminders that would be sent, without sending them.",
        )

    def handle(self, *args, **options):
        summary = notify_referents_pap_formation_reminder(dry_run=options["dry_run"])

        if options["dry_run"]:
            for line in summary:
                self.stdout.write(line)
