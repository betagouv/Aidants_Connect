import io
import hashlib
import qrcode
from pathlib import Path
from datetime import date

from django.conf import settings


def generate_sha256_hash(value):
    if not type(value) == bytes:
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


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
    base_path = Path(__file__).resolve().parent
    file_path = (base_path / filename).resolve()
    with open(file_path, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        file_readable_hash = generate_sha256_hash(bytes)
        return file_readable_hash


def generate_mandat_print_hash(aidant, usager, demarches, expiration_date):
    demarches.sort()
    mandat_print_data = {
        "aidant_id": aidant.id,
        "creation_date": date.today().isoformat(),
        "demarches_list": ",".join(demarches),
        "expiration_date": expiration_date.date().isoformat(),
        "organisation_id": aidant.organisation.id,
        "template_hash": generate_file_sha256_hash(settings.MANDAT_TEMPLATE_PATH),
        "usager_sub": usager.sub,
    }
    sorted_mandat_print_data = dict(sorted(mandat_print_data.items()))
    mandat_print_string = ",".join(
        str(x) for x in list(sorted_mandat_print_data.values())
    )
    return generate_sha256_hash(mandat_print_string + settings.MANDAT_PRINT_SALT)


def validate_mandat_print_hash(mandat_print_string, mandat_print_hash):
    new_mandat_print_hash = generate_sha256_hash(
        mandat_print_string + settings.MANDAT_PRINT_SALT
    )
    return new_mandat_print_hash == mandat_print_hash


def generate_qrcode_png(string: str):
    stream = io.BytesIO()
    img = qrcode.make(string)
    img.save(stream, "PNG")
    return stream.getvalue()
