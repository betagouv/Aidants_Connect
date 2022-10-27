from datetime import datetime
from logging import Logger
from zoneinfo import ZoneInfo

from django.conf import settings

from celery import shared_task
from celery.utils.log import get_task_logger
from metabasepy import Client

from aidants_connect_web.models import HabilitationRequest


@shared_task
def import_pix_results(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    username = settings.PIX_METABASE_USER
    password = settings.PIX_METABASE_PASSWORD
    card_id = settings.PIX_METABASE_CARD_ID
    cli = Client(
        username=username, password=password, base_url="https://metabase.pix.fr"
    )
    cli.authenticate()
    logger.info("Sucessfully authenticated to PIX database.")
    json_result = cli.cards.download(card_id=card_id, format="json")

    for person in json_result:
        date_test_pix = datetime.strptime(
            person["date d'envoi"], "%Y-%m-%d"
        ).astimezone(ZoneInfo("Europe/Paris"))
        aidants = HabilitationRequest.objects.filter(email=person["email saisi"])
        if aidants.exists():
            aidant_a_former = aidants[0]
            aidant_a_former.test_pix_passed = True
            aidant_a_former.date_test_pix = date_test_pix
            aidant_a_former.save()

    logger.info("Sucessfully updated PIX results")
