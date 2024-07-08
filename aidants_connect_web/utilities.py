import hashlib
import time
from datetime import date, datetime
from pathlib import Path
from re import sub
from typing import TYPE_CHECKING, Optional, Union

from django.conf import settings

if TYPE_CHECKING:
    from aidants_connect_web.models import Aidant, Connection, Usager


def generate_sha256_hash(value: bytes):
    """
    Generate a SHA-256 hash
    https://docs.python.org/3/library/hashlib.html
    SHA-256 is a hash function that takes bytes as input, and returns a hash
    The length of the hash is 64 characters
    To add a salt, concatenate the string with the salt ('string'+'salt')
    You must encode your string to bytes beforehand ('stringsalt'.encode())
    :param value: bytes
    :return: a hash (string) of 64 characters
    """
    return hashlib.sha256(value).hexdigest()


def generate_file_sha256_hash(filename):
    """
    Generate a SHA-256 hash of a file
    """
    base_path = Path(__file__).resolve().parent
    file_path = (base_path / filename).resolve()
    with open(file_path, "rb") as f:
        file_bytes = f.read()  # read entire file as bytes
        file_readable_hash = generate_sha256_hash(file_bytes)
        return file_readable_hash


def validate_attestation_hash(attestation_string, attestation_hash):
    attestation_string_with_salt = attestation_string + settings.ATTESTATION_SALT
    new_attestation_hash = generate_sha256_hash(
        attestation_string_with_salt.encode("utf-8")
    )
    return new_attestation_hash == attestation_hash


def generate_attestation_hash(
    aidant: "Aidant",
    usager: "Usager",
    demarches: Union[str, list],
    expiration_date: datetime,
    creation_date: str = date.today().isoformat(),
    mandat_template_path: str = settings.MANDAT_TEMPLATE_PATH,
    organisation_id: Optional[int] = None,
):
    organisation_id = (
        aidant.organisation.id if organisation_id is None else organisation_id
    )

    if isinstance(demarches, str):
        demarches_list = demarches
    else:
        demarches.sort()
        demarches_list = ",".join(demarches)

    attestation_data = {
        "aidant_id": aidant.id,
        "creation_date": creation_date,
        "demarches_list": demarches_list,
        "expiration_date": expiration_date.date().isoformat(),
        "organisation_id": organisation_id,
        "template_hash": generate_file_sha256_hash(f"templates/{mandat_template_path}"),
        "usager_sub": usager.sub,
    }
    sorted_attestation_data = dict(sorted(attestation_data.items()))
    attestation_string = ";".join(
        str(x) for x in list(sorted_attestation_data.values())
    )
    attestation_string_with_salt = attestation_string + settings.ATTESTATION_SALT
    return generate_sha256_hash(attestation_string_with_salt.encode("utf-8"))


def mandate_template_path():
    return settings.MANDAT_TEMPLATE_PATH


def generate_id_token(connection: "Connection"):
    return {
        # The audience, the Client ID of your Auth0 Application
        "aud": settings.FC_AS_FI_ID,
        # The expiration time. in the format "seconds since epoch"
        # TODO Check if 10 minutes is not too much
        "exp": int(time.time()) + settings.FC_CONNECTION_AGE,  # The issued at time
        "iat": int(time.time()),  # The issuer,  the URL of your Auth0 tenant
        "iss": f"https://{sub(r'^https?://', '', settings.HOST)}",  # The unique identifier of the user  # noqa:E501
        "sub": connection.usager.sub,
        "nonce": connection.nonce,
        "acr": "eidas1",
    }
