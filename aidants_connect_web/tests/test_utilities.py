from django.conf import settings
from django.test import TestCase, TransactionTestCase, tag

from aidants_connect_web.models import IdGenerator
from aidants_connect_web.utilities import generate_new_datapass_id, generate_sha256_hash


@tag("utilities")
class UtilitiesTests(TestCase):
    def test_generate_sha256_hash(self):
        hash_123 = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
        hash_123salt = (
            "81d40d94fee4fb4eeb1a21bb7adb93c06aad35b929c1a2b024ae33b3a9b79e23"
        )
        self.assertRaises(TypeError, generate_sha256_hash, "123")
        self.assertEqual(generate_sha256_hash("123".encode()), hash_123)
        self.assertEqual(generate_sha256_hash("123".encode("utf-8")), hash_123)
        self.assertEqual(
            generate_sha256_hash("123".encode() + "salt".encode()), hash_123salt
        )
        self.assertEqual(generate_sha256_hash("123salt".encode()), hash_123salt)
        self.assertEqual(len(generate_sha256_hash("123salt".encode())), 64)


@tag("utilities")
class GenerateDatapassIdTests(TransactionTestCase):
    def test_generate_new_datapass_id(self):
        IdGenerator.objects.get_or_create(
            code=settings.DATAPASS_CODE_FOR_ID_GENERATOR, defaults={"last_id": 10000}
        )
        self.assertEqual(generate_new_datapass_id(), 10001)
        self.assertEqual(generate_new_datapass_id(), 10002)
