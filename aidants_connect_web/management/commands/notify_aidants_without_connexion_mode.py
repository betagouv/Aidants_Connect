from argparse import BooleanOptionalAction

from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import notify_aidants_without_connexion_mode


class Command(BaseCommand):
    help = (
        "Notifies the referents of active aidants who have no connexion mode "
        "(neither TOTP card nor OTP app) associated with their account. Aidants "
        "whose account has been activated 15 days ago are notified on the run; "
        "on the 20th of each month, every aidant activated for more than 15 days "
        "is notified."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--monthly",
            action=BooleanOptionalAction,
            help=(
                "Force the run mode: --monthly notifies every aidant activated "
                "for more than 15 days, --no-monthly only notifies aidants "
                "activated exactly 15 days ago. By default, the mode is chosen "
                "from the current day."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the notifications that would be sent, without sending them.",
        )

    def handle(self, *args, **options):
        summary = notify_aidants_without_connexion_mode(
            monthly=options["monthly"], dry_run=options["dry_run"]
        )

        if options["dry_run"]:
            for line in summary:
                self.stdout.write(line)
