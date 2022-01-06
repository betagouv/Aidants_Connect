from django.core.management.base import BaseCommand

from aidants_connect_web.tasks import delete_duplicated_static_tokens


class Command(BaseCommand):
    help = (
        "Deletes duplicated static tokens of aidants and static tokens of aidants "
        "with confirmed totp cards"
    )

    def handle(self, *args, **options):
        delete_duplicated_static_tokens()
