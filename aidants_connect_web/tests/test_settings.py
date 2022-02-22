import os
import uuid
from unittest import TestCase

from aidants_connect.settings import getenv_bool


class Test(TestCase):
    env_key = str(uuid.uuid4())

    def setUp(self) -> None:
        try:
            del os.environ[self.env_key]
        except KeyError:
            pass

    def test_getenv_bool_env_is_not_set(self):
        self.assertRaises(ValueError, getenv_bool, self.env_key)

    def test_getenv_bool_env_is_not_set_default_value(self):
        self.assertIs(True, getenv_bool(self.env_key, True))

    def test_getenv_bool_env_integer_value(self):
        os.environ[self.env_key] = "0"
        self.assertIs(False, getenv_bool(self.env_key))
        os.environ[self.env_key] = "1"
        self.assertIs(True, getenv_bool(self.env_key))

    def test_getenv_bool_env_bool_value(self):
        os.environ[self.env_key] = "false"
        self.assertIs(False, getenv_bool(self.env_key))
        os.environ[self.env_key] = "False"
        self.assertIs(False, getenv_bool(self.env_key))
        os.environ[self.env_key] = "FALSE"
        self.assertIs(False, getenv_bool(self.env_key))
        os.environ[self.env_key] = "no"
        self.assertIs(False, getenv_bool(self.env_key))
        os.environ[self.env_key] = "true"
        self.assertIs(True, getenv_bool(self.env_key))
        os.environ[self.env_key] = "True"
        self.assertIs(True, getenv_bool(self.env_key))
        os.environ[self.env_key] = "TRUE"
        self.assertIs(True, getenv_bool(self.env_key))
        os.environ[self.env_key] = "yes"
        self.assertIs(True, getenv_bool(self.env_key))

    def test_getenv_bool_env_invalid_value(self):
        os.environ[self.env_key] = "-1"
        self.assertRaises(ValueError, getenv_bool, self.env_key)
        self.assertIs(True, getenv_bool(self.env_key, True))
