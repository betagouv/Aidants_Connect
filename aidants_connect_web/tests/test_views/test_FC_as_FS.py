from datetime import datetime, timedelta
import mock

from django.conf import settings
from django.test import tag, TestCase
from django.test.client import Client

from freezegun import freeze_time
import jwt
from pytz import timezone

from aidants_connect_web.models import Connection, Usager
from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.views.FC_as_FS import get_user_info


fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("new_mandat", "FC_as_FS")
class FCAuthorize(TestCase):
    def setUp(self):
        Connection.objects.create(id=1, demarches=["argent", "papiers"], duree=1)

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
        self.aidant = AidantFactory()
        date = datetime(2019, 1, 14, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris"))
        self.epoch_date = date.timestamp()

        self.connection = Connection.objects.create(
            demarches=["argent", "papiers"],
            duree=1,
            state="test_state",
            connection_type="FS",
            nonce="test_nonce",
            id=1,
            expires_on=date + timedelta(minutes=5),
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

    date_expired = date + timedelta(seconds=settings.FC_CONNECTION_AGE + 1200)

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
        url = (
            "https://fcp.integ01.dev-franceconnect.fr/api/v1/logout?id_token_hint=b'e"
            "yJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyMTEyODY0MzNlMzljY2UwMWRi"
            "NDQ4ZDgwMTgxYmRmZDAwNTU1NGIxOWNkNTFiM2ZlNzk0M2Y2YjNiODZhYjZlIiwiZXhwIjox"
            "NTQ3NDM2MDk0LjAsImlhdCI6MTU0NzQzNDg5NC4wLCJpc3MiOiJodHRwOi8vZnJhbmNlY29u"
            "bmVjdC5nb3V2LmZyIiwic3ViIjoxMjMsIm5vbmNlIjoidGVzdF9ub25jZSJ9.vqQoJ3vovqC"
            "nbXzu7_V7bgsIZH6PPLBkIzeWnSp2sqo'&state=test_state&post_logout_redirect_"
            "uri=http://localhost:3000/logout-callback"
        )
        self.assertRedirects(response, url, fetch_redirect_response=False)

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

        url = (
            "https://fcp.integ01.dev-franceconnect.fr/api/v1/logout?id_token_hint=b'ey"
            "J0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyMTEyODY0MzNlMzljY2UwMWRiND"
            "Q4ZDgwMTgxYmRmZDAwNTU1NGIxOWNkNTFiM2ZlNzk0M2Y2YjNiODZhYjZlIiwiZXhwIjoxNTQ"
            "3NDM2MDk0LjAsImlhdCI6MTU0NzQzNDg5NC4wLCJpc3MiOiJodHRwOi8vZnJhbmNlY29ubmV"
            "jdC5nb3V2LmZyIiwic3ViIjo0NTYsIm5vbmNlIjoidGVzdF9ub25jZSJ9.tuHulPV1IhyS7UZ"
            "8q4QWrg8EAeF1vgpFOr-5vV-ags4'&state=test_state&post_logout_redirect_uri="
            "http://localhost:3000/logout-callback"
        )
        self.assertRedirects(response, url, fetch_redirect_response=False)


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
        self.assertEqual(usager.email, "test@test.com")
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

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_formated_user_without_birthplace_outputs_usager(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={
                "given_name": "Flo",
                "family_name": "Durand",
                "sub": "123",
                "preferred_username": "Flo",
                "birthdate": "1981-07-27",
                "gender": "male",
                "birthplace": "",
                "birthcountry": "99131",
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response

        usager, error = get_user_info("abc", "def")

        self.assertEqual(usager.given_name, "Flo")
        self.assertEqual(error, None)
