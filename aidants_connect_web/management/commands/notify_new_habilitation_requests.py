from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import notify_new_habilitation_requests


class Command(BaseCommand):
    help = "Notifies staff administrators that new habilitation requests are to be seen"

    def handle(self, *args, **options):
        notify_new_habilitation_requests()
