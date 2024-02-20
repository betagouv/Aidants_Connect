import logging

from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import email_activity_tracking_warning

logger = logging.getLogger()


class Command(BaseCommand):
    help = "Notifies aidants who have no activity for 90 days"

    def handle(self, *args, **options):
        email_activity_tracking_warning(logger=logger)
