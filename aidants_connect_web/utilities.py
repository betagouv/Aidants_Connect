import hashlib


def generate_sha256_hash(value):
    if not type(value) == bytes:
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()
