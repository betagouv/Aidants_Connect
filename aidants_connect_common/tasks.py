from logging import Logger
from re import sub as re_sub

from django.db.models import Q

import requests as python_request
from celery import shared_task
from celery.utils.log import get_task_logger
from requests import RequestException

from aidants_connect_habilitation.models import Manager, OrganisationRequest
from aidants_connect_web.models import Organisation


@shared_task
def autofill_insee_code(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    base_url = "https://datanova.laposte.fr/api/records/1.0/search/"

    orgs = Organisation.objects.filter(
        Q(city_insee_code__isnull_or_blank=True) & ~Q(zipcode="0")
    ).all()

    manager = Manager.objects.filter(
        Q(city_insee_code__isnull_or_blank=True) & ~Q(zipcode="0")
    ).all()

    org_req = OrganisationRequest.objects.filter(
        Q(city_insee_code__isnull_or_blank=True) & ~Q(zipcode="0")
    ).all()

    items = [*orgs, *manager, *org_req]

    for item in items:
        normalized_city = re_sub(r"\W+", " ", item.city or "").upper()
        try:
            result = python_request.get(
                base_url,
                params={
                    "q": f"{normalized_city} {item.zipcode}",
                    "dataset": "laposte_hexasmal",
                },
                headers={"Accept": "application/json"},
            ).json()

            records = result.get("records")
            if records and len(records) == 1:
                insee_code = records[0]["fields"]["code_commune_insee"]
                logger.info(f"Updating {item} with city insee code {insee_code}")
                item.city_insee_code = insee_code
                item.save()
            else:
                logger.info(f"No insee code returned by HTTP API for {item}")

        except (RequestException, KeyError) as e:
            logger.warning("Address API did not respond correctly", exc_info=e)
            continue
