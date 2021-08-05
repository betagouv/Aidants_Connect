from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import notify_no_totp_workers


class Command(BaseCommand):
    help = (
        "Notifies managers of community workers (aidants) "
        "who have not yet paired their TOTP card"
    )

    def handle(self, *args, **options):
        notify_no_totp_workers()
