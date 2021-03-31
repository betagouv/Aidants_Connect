from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import notify_soon_expired_mandates


class Command(BaseCommand):
    help = "Notifies organisations by email about soon to be expired mandates"

    def handle(self, *args, **options):
        notify_soon_expired_mandates()
