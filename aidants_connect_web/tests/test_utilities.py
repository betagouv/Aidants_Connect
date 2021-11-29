import os

from django.test import tag, TestCase

from aidants_connect_web.models import Aidant, Organisation

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

from aidants_connect_web.utilities import create_first_user_organisation_and_token
from aidants_connect_web.utilities import generate_sha256_hash

from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from unittest import mock


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
class CreateFirstUserTests(TestCase):
    def test_dont_create_if_user_exists(self):
        AidantFactory()
        self.assertEqual(1, len(Aidant.objects.all()))
        self.assertIsNone(create_first_user_organisation_and_token())
        self.assertEqual(1, len(Aidant.objects.all()))

    def test_dont_create_if_organisation_exists(self):
        OrganisationFactory()
        self.assertEqual(1, len(Organisation.objects.all()))
        self.assertIsNone(create_first_user_organisation_and_token())
        self.assertEqual(1, len(Organisation.objects.all()))

    def test_dont_create_without_all_venv(self):
        self.assertEqual(0, len(Aidant.objects.all()))
        self.assertEqual(0, len(Organisation.objects.all()))
        self.assertIsNone(create_first_user_organisation_and_token())
        self.assertEqual(0, len(Organisation.objects.all()))
        self.assertEqual(0, len(Aidant.objects.all()))

    @mock.patch.dict(os.environ, {"INIT_ORGA_NAME": "Donjons et Siphons"})
    @mock.patch.dict(os.environ, {"INIT_ADMIN_USERNAME": "mario.brossse@world.fr"})
    @mock.patch.dict(os.environ, {"INIT_ADMIN_PASSWORD": "PEACHforEVER"})
    def test_dont_create_without_one_venv(self):
        self.assertEqual(0, len(Aidant.objects.all()))
        self.assertEqual(0, len(Organisation.objects.all()))
        self.assertIsNone(create_first_user_organisation_and_token())
        self.assertEqual(0, len(Organisation.objects.all()))
        self.assertEqual(0, len(Aidant.objects.all()))

    @mock.patch.dict(os.environ, {"INIT_ORGA_NAME": "Donjons et Siphons"})
    @mock.patch.dict(os.environ, {"INIT_ADMIN_USERNAME": "mario.brossse@world.fr"})
    @mock.patch.dict(os.environ, {"INIT_ADMIN_PASSWORD": "PEACHforEVER"})
    @mock.patch.dict(os.environ, {"INIT_TOKEN": "12345"})
    def test_dont_create_without_with_a_invalid_token(self):
        self.assertEqual(0, len(Aidant.objects.all()))
        self.assertEqual(0, len(Organisation.objects.all()))
        self.assertIsNone(create_first_user_organisation_and_token())
        self.assertEqual(0, len(Organisation.objects.all()))
        self.assertEqual(0, len(Aidant.objects.all()))

    @mock.patch.dict(os.environ, {"INIT_ORGA_NAME": "Donjons et Siphons"})
    @mock.patch.dict(os.environ, {"INIT_ADMIN_USERNAME": "mario.brossse@world.fr"})
    @mock.patch.dict(os.environ, {"INIT_ADMIN_PASSWORD": "PEACHforEVER"})
    @mock.patch.dict(os.environ, {"INIT_TOKEN": "123456"})
    def test_create_all_object(self):
        self.assertEqual(0, len(Aidant.objects.all()))
        self.assertEqual(0, len(Organisation.objects.all()))
        user = create_first_user_organisation_and_token()
        self.assertIsNotNone(user)
        self.assertEqual(1, len(Organisation.objects.all()))
        self.assertEqual(1, len(Aidant.objects.all()))
        self.assertEqual(1, len(StaticToken.objects.all()))
        self.assertEqual(1, len(StaticDevice.objects.all()))

        self.assertEqual(user.username, "mario.brossse@world.fr")
        self.assertEqual(Organisation.objects.first().name, "Donjons et Siphons")

        self.assertEqual(StaticToken.objects.first().token, "123456")
