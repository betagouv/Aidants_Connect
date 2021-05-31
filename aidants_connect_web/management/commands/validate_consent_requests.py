from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aidants_connect_web.constants import JournalActionKeywords
from aidants_connect_web.models import Journal


class Command(BaseCommand):
    help = (
        "Validates all sent consent requests without response. "
        "This function exists for test purposes. DO NOT CALL IN PRODUCTION!"
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "This command should not be called on a production "
                "environement; Set DEBUG to a truthy value to enable this "
                "command"
            )

        for request in Journal.objects.filter(
            action=JournalActionKeywords.CONSENT_REQUEST_SENT
        ):
            if not Journal.find_consent_denial_or_agreement(
                request.user_phone, request.consent_request_tag
            ):
                Journal.log_agreement_of_consent_received(
                    aidant=request.aidant,
                    user_phone=request.user_phone,
                    consent_request_tag=request.consent_request_tag,
                    demarche=request.demarche,
                    duree=request.duree,
                )
