from datetime import datetime
from logging import Logger
from zoneinfo import ZoneInfo

from django.conf import settings

from celery import shared_task
from celery.utils.log import get_task_logger
from metabasepy import Client

from aidants_connect_web.models import HabilitationRequest

from .insee_utils import get_client_insee_api
from .utils import get_and_save_insee_informations, get_orga_req_without_legal_category


def update_legal_category_for_organisation_request(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    api = get_client_insee_api()
    orga_reqs = get_orga_req_without_legal_category()
    for orga_req in orga_reqs:
        get_and_save_insee_informations(orga_req, api)


def update_pix_and_create_aidant(json_result):
    for person in json_result:
        date_test_pix = datetime.strptime(
            person["date d'envoi"], "%Y-%m-%d"
        ).astimezone(ZoneInfo("Europe/Paris"))
        aidants_a_former = HabilitationRequest.objects.filter(
            email=person["email saisi"]
        )

        if aidants_a_former.exists():
            for aidant_a_former in aidants_a_former:
                if not aidant_a_former.test_pix_passed:
                    aidant_a_former.test_pix_passed = True
                    aidant_a_former.date_test_pix = date_test_pix
                    aidant_a_former.save()
                    if aidant_a_former.formation_done:
                        aidant_a_former.validate_and_create_aidant()


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

    update_pix_and_create_aidant(json_result)

    logger.info("Sucessfully updated PIX results")
