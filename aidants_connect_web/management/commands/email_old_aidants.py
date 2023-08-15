from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import email_old_aidants


class Command(BaseCommand):
    help = "Sends a warning to all aidants that did not connect recently"

    def handle(self, *args, **options):
        email_old_aidants()
