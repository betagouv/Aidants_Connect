import json
import os
from gettext import ngettext
from logging import Logger
from re import sub as re_sub

from django.core.mail import send_mail
from django.core.management import call_command
from django.db.models import Q
from django.utils.timezone import now

import requests as python_request
from celery import shared_task
from celery.utils.log import get_task_logger
from requests import RequestException

from aidants_connect import settings
from aidants_connect_common.models import FormationAttendant, FormationOrganization
from aidants_connect_common.utils import render_email
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


def get_body_email_formation_organization_new_attendants(attendants):
    text_message, html_message = render_email(
        "email/formation_organization_new_attendants.mjml",
        {
            "attendants": attendants,
            "detail_attendants": (
                settings.EMAIL_ORGANISATION_FORMATION_NEW_ATTENDANT_GRIST_LINK
            ),
        },
    )
    return text_message, html_message


def get_attendants_for_organization(organization):
    attendants = (
        FormationAttendant.objects.filter(
            formation__organisation=organization, organization_warned_at__isnull=True
        )
        .prefetch_related("formation")
        .order_by("formation")
    )
    return attendants


@shared_task
def email_formation_organization_new_attendants():
    orgs = FormationOrganization.objects.warnable_about_new_attendants()

    for org in orgs:

        attendants = get_attendants_for_organization(org)

        text_message, html_message = (
            get_body_email_formation_organization_new_attendants(attendants)
        )

        send_mail(
            from_email=settings.AC_CONTACT_EMAIL,
            subject=ngettext(
                "Nouvelle inscription à une formation Aidants Connect",
                "Nouvelles inscriptions à des formations Aidants Connect",
                len(attendants),
            ),
            recipient_list=org.contacts,
            message=text_message,
            html_message=html_message,
        )

        attendants.update(organization_warned_at=now())
