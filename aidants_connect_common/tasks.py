import json
import os
from logging import Logger
from re import sub as re_sub

from django.core.management import call_command
from django.db.models import Q

import requests as python_request
from celery import shared_task
from celery.utils.log import get_task_logger
from requests import RequestException

from aidants_connect import settings
from aidants_connect_habilitation.models import Manager, OrganisationRequest
from aidants_connect_web.models import Organisation


@shared_task
def autofill_insee_code(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    base_url = "https://api-adresse.data.gouv.fr/search/"

    file_path = os.path.join(settings.STATIC_ROOT, "insee_files/communes_2022.json")
    f = open(file_path)
    data_insee = json.load(f)

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
                    "q": f"{normalized_city} {item.zipcode}&type=municipality",
                },
                headers={"Accept": "application/json"},
            ).json()

            records = result.get("features")
            if records:
                insee_code = records[0]["properties"]["citycode"]
                logger.info(f"Updating {item} with city insee code {insee_code}")
                item.city_insee_code = insee_code
                for city in data_insee:
                    if city["code"] == insee_code:
                        departement_insee_code = city["departement"]
                        break
                logger.info(
                    f"Updating {item} with departement code {departement_insee_code}"
                )
                item.department_insee_code = departement_insee_code
                item.save()
            else:
                logger.info(f"No insee code returned by HTTP API for {item}")

        except (RequestException, KeyError) as e:
            logger.warning("Address API did not respond correctly", exc_info=e)
            continue


@shared_task
def clean_blocklist():
    call_command("clean_blocklist")
