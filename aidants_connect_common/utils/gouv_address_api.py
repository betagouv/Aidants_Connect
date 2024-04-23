import logging
from enum import Enum
from typing import List, Union

from django.conf import settings

import requests as python_request
from pydantic import BaseModel, validator
from requests.exceptions import RequestException

logger = logging.getLogger()


class AddressType(Enum):
    HOUSENUMBER = "housenumber"
    STREET = "street"
    LOCALITY = "locality"
    MUNICIPALITY = "municipality"

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class Context(BaseModel):
    department_number: str
    department_name: str
    region: str


class Address(BaseModel):
    id: str
    name: str
    label: str
    score: float
    postcode: str
    city: str
    citycode: str
    context: Context
    type: AddressType

    @validator("context", pre=True)
    def parse_context(cls, value: Union[str, dict, Context]):
        if isinstance(value, Context):
            return value

        if isinstance(value, str):
            department_number, department_name, *region = value.split(",")
            region = region[0] if len(region) == 1 else department_name
        else:
            department_number, department_name, region = (
                value["department_number"],
                value["department_name"],
                value["region"],
            )
        return Context(
            department_number=department_number.strip(),
            department_name=department_name.strip(),
            region=region.strip(),
        )


def search_adresses(query_string: str) -> List[Address]:
    """
    Takes an address manually provided by a user and searches on government API
    for data on this address.

    The API used is documented on https://adresse.data.gouv.fr/api-doc/adresse
    """
    # Mock the service when under tests
    if (
        settings.GOUV_ADDRESS_SEARCH_API_DISABLED
        and settings.GOUV_ADDRESS_SEARCH_API_UNDER_TEST
    ):

        return [
            Address(
                id="75107_8909",
                name="Avenue de Ségur",
                label=query_string,
                score=0.95,
                postcode="75007",
                city="Paris",
                citycode="75107",
                context=Context(
                    department_number="75",
                    department_name="Paris",
                    region="Île-de-France",
                ),
                type=AddressType.STREET,
            )
        ]

    if settings.GOUV_ADDRESS_SEARCH_API_DISABLED:
        return []

    try:
        result = python_request.get(
            settings.GOUV_ADDRESS_SEARCH_API_BASE_URL,
            params={"q": query_string},
            headers={"Accept": "application/json"},
        ).json()
    except RequestException as e:
        logger.warning("Address API did not respond correctly", exc_info=e)
        return []

    # The API returns a GeoJSON object. We proces it to only
    # extract relevent information in `result.properties[i].features`
    return [Address(**item["properties"]) for item in result["features"]]
