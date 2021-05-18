from random import randint
from typing import Optional, Union
from uuid import uuid4

from django.test import tag, TestCase
from phonenumbers import PhoneNumber, format_number, PhoneNumberFormat

from aidants_connect_web.utilities import generate_sha256_hash


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


class SmsTestUtils:
    @classmethod
    def get_request_data(
        cls,
        sms_tag: Optional[str] = None,
        user_phone: Union[PhoneNumber, str] = "0 800 840 800",
        message: str = "oui",
    ):
        user_phone = (
            format_number(user_phone, PhoneNumberFormat.E164)
            if isinstance(user_phone, PhoneNumber)
            else user_phone
        )

        return {
            "shortcode": "82555",
            "tag": sms_tag if sms_tag else str(uuid4()),
            "id": str(randint(1, 10_000)),
            "senderid": user_phone,
            "message": message,
        }

    @classmethod
    def patched_safe_client_post(cls, *args, **kwargs):
        """
        Patched version of aidants_connect_web.sms_api.SafeClient to prevent test fails
        """
        return {"validReceivers": kwargs["receivers"]}
