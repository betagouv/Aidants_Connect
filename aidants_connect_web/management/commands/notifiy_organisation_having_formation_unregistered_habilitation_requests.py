from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import (
    notifiy_organisation_having_formation_unregistered_habilitation_requests,
)


class Command(BaseCommand):
    help = (
        "Deletes duplicated static tokens of aidants and static tokens of aidants "
        "with confirmed totp cards"
    )

    def handle(self, *args, **options):
        notifiy_organisation_having_formation_unregistered_habilitation_requests()
