import hashlib


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
