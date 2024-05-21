from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote, urlencode

from django.conf import settings
from django.db.models import Value
from django.db.models.functions import Concat

import requests
from pydantic import BaseModel
from requests import RequestException

from aidants_connect_common.utils import join_url_parts

logger = logging.getLogger()


def delete_mandats_and_clean_journal(item, str_today):
    from aidants_connect_web.models import Journal

    for mandat in item.mandats.all():
        entries = Journal.objects.filter(mandat=mandat)
        mandat_str_add_inf = (
            f"Added by clean_journal_entries_and_delete_mandats :"
            f"\n Relatif au mandat supprimé {mandat} le {str_today}"
        )
        entries.update(
            mandat=None,
            additional_information=Concat(
                "additional_information", Value(mandat_str_add_inf)
            ),
        )
        mandat.delete()


class Session(BaseModel):
    id: str
    estimated_started_at: datetime


class Participant(BaseModel):
    id: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    adresse_email_professionnelle_utilisee_dans_lhabilitation: str = ""
    job_title: str = ""
    structure: str = ""
    address: str = ""
    city: str = ""
    region: list[str] = []

    def get_email(self):
        return (
            (
                self.adresse_email_professionnelle_utilisee_dans_lhabilitation
                or self.email
            )
            .casefold()
            .strip()
        )


class LiveStormApi:
    LIVESTORM_BASE_URL = "https://api.livestorm.co/v1"

    def __init__(self, logger: logging.Logger = logger):
        if not settings.LIVESTORM_API_KEY:
            raise EnvironmentError(
                "Environement variable LIVESTORM_API_KEY must be set"
            )
        self._logger = logger

    def get_event_id(self, event_name: str) -> str | None:
        url = join_url_parts(self.LIVESTORM_BASE_URL, "/events")

        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": settings.LIVESTORM_API_KEY,
                    "Accept": "application/vnd.api+json",
                },
            ).json()

            event = next(
                (
                    event
                    for event in response["data"]
                    if event["attributes"]["title"].casefold().strip()
                    == event_name.casefold().strip()
                ),
                None,
            )
            return event["id"]

        except (RequestException, KeyError) as e:
            self._logger.error(f"API {url} did not respond correctly", exc_info=e)
            return None

    def get_sessions_id_for_event(self, event_id: str) -> list[Session]:
        url = join_url_parts(self.LIVESTORM_BASE_URL, f"/events/{event_id}/sessions")

        result = []
        next_page = 0

        try:
            while isinstance(next_page, int):
                params = urlencode(
                    {
                        "page[size]": 100,
                        "page[number]": next_page,
                        "filter[status]": "upcoming",
                    },
                    quote_via=lambda string, _, encoding, errors: quote(
                        string, "", encoding, errors
                    ),
                )

                response = requests.get(
                    f"{url}?{params}",
                    headers={
                        "Authorization": settings.LIVESTORM_API_KEY,
                        "Accept": "application/vnd.api+json",
                    },
                ).json()

                next_page = response["meta"]["next_page"]

                for item in response["data"]:
                    result.append(
                        Session(
                            id=item["id"],
                            estimated_started_at=item["attributes"][
                                "estimated_started_at"
                            ],
                        )
                    )

            return result

        except (RequestException, KeyError) as e:
            self._logger.error(f"API {url} did not respond correctly", exc_info=e)
            return []

    def get_people_for_session(self, event_id: str) -> list[Participant]:
        url = join_url_parts(self.LIVESTORM_BASE_URL, f"/sessions/{event_id}/people")

        try:
            result = []
            next_page = 0

            while isinstance(next_page, int):
                params = urlencode(
                    {
                        "page[size]": 100,
                        "page[number]": next_page,
                    },
                    quote_via=lambda string, _, encoding, errors: quote(
                        string, "", encoding, errors
                    ),
                )

                response = requests.get(
                    f"{url}?{params}",
                    headers={
                        "Authorization": settings.LIVESTORM_API_KEY,
                        "Accept": "application/vnd.api+json",
                    },
                ).json()

                next_page = response["meta"]["next_page"]

                for item in response["data"]:
                    result.append(
                        Participant(
                            id=item["id"],
                            **{
                                field["id"]: field["value"]
                                for field in item["attributes"]["registrant_detail"][
                                    "fields"
                                ]
                                if field["value"]
                            },
                        )
                    )

            return result

        except (RequestException, KeyError) as e:
            self._logger.error(f"API {url} did not respond correctly", exc_info=e)
            return []
