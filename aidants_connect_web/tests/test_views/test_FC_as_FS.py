import mock
import jwt
from pytz import timezone
from datetime import datetime, timedelta
from freezegun import freeze_time

from django.test import TestCase
from django.conf import settings

from aidants_connect_web.models import Connection, CONNECTION_EXPIRATION_TIME

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


class FCAuthorize(TestCase):
    def test_well_formatted_request_creates_connection(self):
        self.client.get("/fc_authorize/")
        connections = Connection.objects.all()
        self.assertEqual(len(connections), 1)


class FCCallback(TestCase):
    date = datetime(2019, 1, 14, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris"))

    @freeze_time(date)
    def setUp(self):
        self.connection = Connection(
            state="test_state", connection_type="FS", nonce="test_nonce"
        )
        self.connection.save()

    def test_no_code_triggers_403(self):
        response = self.client.get("/callback/", data={"state": "test_state"})
        self.assertEqual(response.status_code, 403)

    def test_no_state_triggers_403(self):
        response = self.client.get("/callback/", data={"code": "test_code"})
        self.assertEqual(response.status_code, 403)

    date_expired = date + timedelta(minutes=CONNECTION_EXPIRATION_TIME + 20)

    @freeze_time(date_expired)
    def test_expired_connection_returns_403(self):
        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        self.assertEqual(response.status_code, 403)

    @freeze_time(date)
    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.post")
    def test_wrong_nonce_when_decoding_returns_403(self, mock_post):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        id_token = {"aud": settings.FC_AS_FS_ID, "nonce": "another_nonce"}
        mock_response.json = mock.Mock(
            return_value={
                "access_token": "b337567e-437a-4167-ba51-8f8b6772980b",
                "token_type": "Bearer",
                "expires_in": 60,
                "id_token": jwt.encode(
                    id_token, settings.FC_AS_FS_SECRET, algorithm="HS256"
                ),
            }
        )

        mock_post.return_value = mock_response
        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        self.assertEqual(response.status_code, 403)
