from contextlib import contextmanager
from unittest import mock
from unittest.mock import Mock
from uuid import uuid4

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from phonenumbers import parse as parse_phone
from redis import Redis
from redis.exceptions import ConnectionError
from requests import Response

from aidants_connect_common.utils import sms_api
from aidants_connect_common.utils.sms_api import (
    AuthInfos,
    OAuthMiddleware,
    SmsApi,
    SmsApiImpl,
    SmsApiMock,
)


@override_settings(
    SMS_API_DISABLED=False,
    LM_SMS_SERVICE_USERNAME="username",
    LM_SMS_SERVICE_PASSWORD="password",
    LM_SMS_SERVICE_BASE_URL="http://localhost",
    LM_SMS_SERVICE_OAUTH2_ENDPOINT=reverse("test_sms_api_token"),
    LM_SMS_SERVICE_SND_SMS_ENDPOINT=reverse("test_sms_api_sms"),
)
class TestSmsApi(TestCase):
    def test_create(self):
        self.assertIsInstance(SmsApi(), SmsApiImpl)

        @contextmanager
        def change_setting(key, value):
            old_value = getattr(settings, key)
            try:
                setattr(settings, key, value)
                yield
            finally:
                setattr(settings, key, old_value)

        for k, v in {
            "SMS_API_DISABLED": True,
            "LM_SMS_SERVICE_BASE_URL": "",
            "LM_SMS_SERVICE_USERNAME": "",
            "LM_SMS_SERVICE_PASSWORD": "",
            "LM_SMS_SERVICE_OAUTH2_ENDPOINT": "",
            "LM_SMS_SERVICE_SND_SMS_ENDPOINT": "",
        }.items():
            with change_setting(k, v):
                self.assertIsInstance(
                    SmsApi(),
                    SmsApiMock,
                    f"settings.{k}={v} generated {SmsApiImpl.__class__}; "
                    f"should have generated {SmsApiMock.__class__}",
                )

    @mock.patch("aidants_connect_common.utils.sms_api.OAuthClient.post")
    def test_send_sms(self, post_mock: Mock):
        response = Response()
        response.status_code = 200
        response.encoding = "utf8"
        response._content = b"{}"
        post_mock.return_value = response

        consent_request_id = str(uuid4())
        SmsApi().send_sms(
            parse_phone("0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION),
            consent_request_id,
            "Prolétaires de tous les pays, unissez-vous.",
        )

        post_mock.assert_called_once_with(
            "http://localhost/third_party_service_mocks/test-sms-api/sms/",
            json={
                "userIds": ["33800840800"],
                "correlationId": consent_request_id,
                "message": "Prolétaires de tous les pays, unissez-vous.",
                "encoding": "Unicode",
            },
        )


class TestOAuthMiddleware(TestCase):
    def setUp(self):
        if hasattr(OAuthMiddleware, "_redis_client"):
            del OAuthMiddleware._redis_client

    @mock.patch("aidants_connect_common.utils.sms_api.Redis.ping")
    @mock.patch(
        "aidants_connect_common.utils.sms_api.Redis.from_url",
        side_effect=Redis.from_url,
    )
    def test_redis_client_is_cached(self, redis_ping: Mock, redis_from_url: Mock):
        redis_ping.return_value = None

        target = OAuthMiddleware(AuthInfos("user", "pass", "http://localhost"))

        self.assertFalse(hasattr(OAuthMiddleware, "_redis_client"))

        client = target.redis_client
        redis_from_url.assert_called()
        redis_from_url.reset_mock()

        self.assertIsNotNone(client)
        self.assertIsInstance(OAuthMiddleware.redis_client, Redis)
        self.assertEqual(client, OAuthMiddleware.redis_client)
        # Redis instance is cached on class
        redis_from_url.assert_not_called()

    @mock.patch("aidants_connect_common.utils.sms_api.Redis.ping")
    @mock.patch("aidants_connect_common.utils.sms_api.logger.warning")
    def test_redis_client_is_not_created_when_no_redis_instance_is_available(
        self, logger_warning: Mock, redis_ping: Mock
    ):
        redis_ping.side_effect = ConnectionError()

        target = OAuthMiddleware(AuthInfos("user", "pass", "http://localhost"))

        self.assertFalse(hasattr(OAuthMiddleware, "_redis_client"))
        self.assertIsNone(target.redis_client)
        self.assertTrue(hasattr(OAuthMiddleware, "_redis_client"))
        logger_warning.assert_called_with(
            f"{sms_api.__file__}: No Redis connection available"
        )
        self.assertIsNone(OAuthMiddleware.redis_client)
