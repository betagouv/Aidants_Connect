import mock
import jwt
from pytz import timezone
from datetime import datetime, timedelta
from freezegun import freeze_time

from django.test import TestCase, tag
from django.test.client import Client
from django.conf import settings

from aidants_connect_web.models import (
    Connection,
    CONNECTION_EXPIRATION_TIME,
    Aidant,
    Usager,
)
from aidants_connect_web.views.FC_as_FS import get_user_info

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("new_mandat", "FC_as_FS")
class FCAuthorize(TestCase):
    def setUp(self):
        Connection.objects.create(id=1, demarches=["argent", "papiers"], duration=1)

    def test_well_formatted_request_fills_connection(self):
        session = self.client.session
        session["connection"] = 1
        session.save()
        self.client.get("/fc_authorize/")
        connection = Connection.objects.get(pk=1)
        self.assertNotEqual(connection.state, "")


@tag("new_mandat", "FC_as_FS")
class FCCallback(TestCase):
    date = datetime(2019, 1, 14, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris"))
    epoch_date = date.timestamp()

    @freeze_time(date)
    def setUp(self):
        self.client = Client()
        self.aidant = Aidant.objects.create_user(
            "thierry@thierry.com", "thierry@thierry.com", "motdepassedethierry"
        )
        date = datetime(2019, 1, 14, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris"))
        self.epoch_date = date.timestamp()

        self.connection = Connection.objects.create(
            demarches=["argent", "papiers"],
            duration=1,
            state="test_state",
            connection_type="FS",
            nonce="test_nonce",
            id=1,
            expiresOn=date + timedelta(minutes=5),
        )
        Connection.objects.create(
            state="test_another_state",
            connection_type="FS",
            nonce="test_another_nonce",
            id=2,
        )

        self.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate="1969-12-15",
            gender="female",
            birthplace="70447",
            birthcountry="99100",
            sub="123",
            email="User@user.domain",
            creation_date="2019-08-05T15:49:13.972Z",
        )

    def test_no_code_triggers_403(self):
        response = self.client.get("/callback/", data={"state": "test_state"})
        self.assertEqual(response.status_code, 403)

    def test_no_state_triggers_403(self):
        response = self.client.get("/callback/", data={"code": "test_code"})
        self.assertEqual(response.status_code, 403)

    def test_non_existing_state_triggers_403(self):
        response = self.client.get(
            "/callback/", data={"state": "wrong_state", "code": "test_code"}
        )
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
        id_token = {"aud": settings.FC_AS_FS_ID, "nonce": "wrong_nonce"}
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
            "/callback/", data={"state": "test_another_state", "code": "test_code"}
        )
        self.assertEqual(response.status_code, 403)

    @freeze_time(date)
    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.post")
    def test_request_existing_user_redirects_to_recap(self, mock_post):
        connection_number = 1

        session = self.client.session
        session["connection"] = connection_number
        session.save()

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        id_token = {
            "aud": settings.FC_AS_FS_ID,
            "exp": self.epoch_date + 600,
            "iat": self.epoch_date - 600,
            "iss": "http://franceconnect.gouv.fr",
            "sub": 123,
            "nonce": "test_nonce",
        }
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
        self.client.force_login(self.aidant)

        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        connection = Connection.objects.get(pk=connection_number)

        self.assertEqual(
            connection.access_token, "b337567e-437a-4167-ba51-8f8b6772980b"
        )

        self.assertRedirects(response, "/logout-callback/")

    @freeze_time(date)
    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.post")
    @mock.patch("aidants_connect_web.views.FC_as_FS.get_user_info")
    def test_request_new_user_redirects_to_recap(self, mock_get_user_info, mock_post):
        connection_number = 1

        session = self.client.session
        session["connection"] = connection_number
        session.save()

        # Creating mock_post
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        id_token = {
            "aud": settings.FC_AS_FS_ID,
            "exp": self.epoch_date + 600,
            "iat": self.epoch_date - 600,
            "iss": "http://franceconnect.gouv.fr",
            "sub": 456,
            "nonce": "test_nonce",
        }
        mock_response.json = mock.Mock(
            return_value={
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 60,
                "id_token": jwt.encode(
                    id_token, settings.FC_AS_FS_SECRET, algorithm="HS256"
                ),
            }
        )

        mock_post.return_value = mock_response

        # creating mock_get_user_info
        mock_get_user_info.return_value = (
            Usager.objects.create(
                given_name="Joséphine",
                family_name="ST-PIERRE",
                preferred_username="ST-PIERRE",
                birthdate="1969-12-15",
                gender="female",
                birthplace="70447",
                birthcountry="99100",
                email="User@user.domain",
            ),
            None,
        )

        self.client.force_login(self.aidant)

        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        mock_get_user_info.assert_called_once_with(
            settings.FC_AS_FS_BASE_URL, "test_access_token"
        )

        connection = Connection.objects.get(pk=connection_number)
        self.assertEqual(connection.usager.given_name, "Joséphine")

        self.assertRedirects(response, "/logout-callback/")


@tag("new_mandat", "FC_as_FS")
class GetUserInfoTests(TestCase):

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_well_formated_user_info_outputs_usager(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={
                "given_name": "Fabrice",
                "family_name": "Mercier",
                "sub": "123",
                "preferred_username": "TROIS",
                "birthdate": "1981-07-27",
                "gender": "female",
                "birthplace": "95277",
                "birthcountry": "99100",
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response

        usager, error = get_user_info("abc", "def")

        self.assertEqual(usager.given_name, "Fabrice")
        self.assertEqual(error, None)

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_badly_formated_user_info_outputs_error(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={
                "family_name": "Mercier",
                "sub": "123",
                "preferred_username": "TROIS",
                "birthdate": "1981-07-27",
                "gender": "female",
                "birthplace": "95277",
                "birthcountry": "99100",
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response
        usager, error = get_user_info("abc", "def")

        self.assertEqual(usager, None)
        self.assertIn("The FranceConnect ID is not complete:", error)
