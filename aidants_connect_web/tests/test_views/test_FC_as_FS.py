from datetime import datetime, timedelta
from freezegun import freeze_time
from pytz import timezone as pytz_timezone
import mock
import jwt

from django.conf import settings
from django.test import override_settings, tag, TestCase
from django.test.client import Client

from aidants_connect_web.models import Connection, Journal, Usager
from aidants_connect_web.tests.factories import AidantFactory, UsagerFactory
from aidants_connect_web.utilities import generate_sha256_hash
from aidants_connect_web.views.FC_as_FS import get_user_info


fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("new_mandat", "FC_as_FS")
class FCAuthorize(TestCase):
    def setUp(self):
        Connection.objects.create(
            id=1, demarches=["argent", "papiers"], duree_keyword="SHORT"
        )

    def test_well_formatted_request_fills_connection(self):
        session = self.client.session
        session["connection"] = 1
        session.save()
        self.client.get("/fc_authorize/")
        connection = Connection.objects.get(pk=1)
        self.assertNotEqual(connection.state, "")


DATE = datetime(2019, 1, 14, 3, 20, 34, 0, tzinfo=pytz_timezone("Europe/Paris"))
TEST_FC_CONNECTION_AGE = 300


@tag("new_mandat", "FC_as_FS")
@override_settings(FC_CONNECTION_AGE=TEST_FC_CONNECTION_AGE)
class FCCallback(TestCase):
    date = DATE

    @freeze_time(date)
    def setUp(self):
        self.client = Client()
        self.aidant = AidantFactory()
        self.epoch_date = DATE.timestamp()
        self.connection = Connection.objects.create(
            demarches=["argent", "papiers"],
            duree_keyword="SHORT",
            state="test_state",
            connection_type="FS",
            nonce="test_nonce",
            id=1,
            expires_on=DATE + timedelta(minutes=5),
            aidant=self.aidant,
        )
        Connection.objects.create(
            state="test_another_state",
            connection_type="FS",
            nonce="test_another_nonce",
            id=2,
        )
        self.usager_sub_fc = "123"
        self.usager_sub = generate_sha256_hash(
            f"{self.usager_sub_fc}{settings.FC_AS_FI_HASH_SALT}".encode()
        )
        self.usager = UsagerFactory(given_name="Joséphine", sub=self.usager_sub)

    @freeze_time(date)
    def test_no_code_triggers_403(self):
        response = self.client.get("/callback/", data={"state": "test_state"})
        self.assertEqual(response.status_code, 403)

    @freeze_time(date)
    def test_no_state_triggers_403(self):
        response = self.client.get("/callback/", data={"code": "test_code"})
        self.assertEqual(response.status_code, 403)

    @freeze_time(date)
    def test_non_existing_state_triggers_403(self):
        response = self.client.get(
            "/callback/", data={"state": "wrong_state", "code": "test_code"}
        )
        self.assertEqual(response.status_code, 403)

    date_expired = DATE + timedelta(seconds=TEST_FC_CONNECTION_AGE + 1)

    @freeze_time(date_expired)
    def test_expired_connection_returns_408(self):
        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        self.assertEqual(response.status_code, 408)

    @freeze_time(date)
    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.post")
    def test_wrong_nonce_when_decoding_returns_403(self, mock_post):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        id_token = {"aud": settings.FC_AS_FS_ID, "nonce": "wrong_nonce"}
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
        response = self.client.get(
            "/callback/", data={"state": "test_another_state", "code": "test_code"}
        )
        self.assertEqual(response.status_code, 403)

    @freeze_time(date)
    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.post")
    @mock.patch("aidants_connect_web.views.FC_as_FS.get_user_info")
    def test_request_existing_user_redirects_to_recap(
        self, mock_get_user_info, mock_post
    ):
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
            "sub": self.usager_sub_fc,
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

        mock_get_user_info.return_value = (self.usager, None)

        self.client.force_login(self.aidant)

        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        mock_get_user_info.assert_called_once_with(self.connection)

        connection = Connection.objects.get(pk=connection_number)

        self.assertEqual(connection.access_token, "test_access_token")
        url = (
            "https://fcp.integ01.dev-franceconnect.fr/api/v1/logout?id_token_hint=b'e"
            "yJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyMTEyODY0MzNlMzljY2UwMWRi"
            "NDQ4ZDgwMTgxYmRmZDAwNTU1NGIxOWNkNTFiM2ZlNzk0M2Y2YjNiODZhYjZlIiwiZXhwIjox"
            "NTQ3NDM2MDk0LjAsImlhdCI6MTU0NzQzNDg5NC4wLCJpc3MiOiJodHRwOi8vZnJhbmNlY29u"
            "bmVjdC5nb3V2LmZyIiwic3ViIjoiMTIzIiwibm9uY2UiOiJ0ZXN0X25vbmNlIn0.QGb2uhgG"
            "wXvKaVT8FXwOzSObtuLrBRKigd7DVJwUG5s'&state=test_state"
            "&post_logout_redirect_uri=http://localhost:3000/logout-callback"
        )
        self.assertRedirects(response, url, fetch_redirect_response=False)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "franceconnect_usager")

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
            "sub": "9b754782705c55ebfe10371c909f62e73a3e09fb566fc5d23040a29fae4e0ebb",
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

        mock_get_user_info.return_value = (
            UsagerFactory(
                given_name="Joséphine",
                family_name="ST-PIERRE",
                preferred_username="ST-PIERRE",
                birthdate="1969-12-15",
                gender=Usager.GENDER_FEMALE,
                birthplace="70447",
                birthcountry=Usager.BIRTHCOUNTRY_FRANCE,
                email="User@user.domain",
                sub="456",
            ),
            None,
        )

        self.client.force_login(self.aidant)

        response = self.client.get(
            "/callback/", data={"state": "test_state", "code": "test_code"}
        )
        mock_get_user_info.assert_called_once_with(self.connection)

        connection = Connection.objects.get(pk=connection_number)
        self.assertEqual(connection.usager.given_name, "Joséphine")

        url = (
            "https://fcp.integ01.dev-franceconnect.fr/api/v1/logout?id_token_hint=b'ey"
            "J0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyMTEyODY0MzNlMzljY2UwMWRiND"
            "Q4ZDgwMTgxYmRmZDAwNTU1NGIxOWNkNTFiM2ZlNzk0M2Y2YjNiODZhYjZlIiwiZXhwIjoxNTQ"
            "3NDM2MDk0LjAsImlhdCI6MTU0NzQzNDg5NC4wLCJpc3MiOiJodHRwOi8vZnJhbmNlY29ubmVj"
            "dC5nb3V2LmZyIiwic3ViIjoiOWI3NTQ3ODI3MDVjNTVlYmZlMTAzNzFjOTA5ZjYyZTczYTNlM"
            "DlmYjU2NmZjNWQyMzA0MGEyOWZhZTRlMGViYiIsIm5vbmNlIjoidGVzdF9ub25jZSJ9.J8048"
            "J_B5MgwQkLzX28yXTDFPB4mTeoyUGW9RSW5YZ4'&state=test_state&post_logout_redi"
            "rect_uri=http://localhost:3000/logout-callback"
        )
        self.assertRedirects(response, url, fetch_redirect_response=False)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "franceconnect_usager")


@tag("new_mandat", "FC_as_FS")
class GetUserInfoTests(TestCase):
    def setUp(self):
        self.usager_sub_fc = "123"
        self.usager_sub = generate_sha256_hash(
            f"{self.usager_sub_fc}{settings.FC_AS_FI_HASH_SALT}".encode()
        )
        self.usager = UsagerFactory(given_name="Joséphine", sub=self.usager_sub)
        self.aidant = AidantFactory()
        self.connection = Connection.objects.create(
            access_token="mock_access_token", aidant=self.aidant,
        )

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_well_formatted_new_user_info_outputs_usager(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={
                "given_name": "Fabrice",
                "family_name": "Mercier",
                "sub": "456",
                "preferred_username": "TROIS",
                "birthdate": "1981-07-27",
                "gender": Usager.GENDER_FEMALE,
                "birthplace": "95277",
                "birthcountry": Usager.BIRTHCOUNTRY_FRANCE,
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response

        usager, error = get_user_info(self.connection)

        self.assertEqual(usager.given_name, "Fabrice")
        self.assertEqual(usager.email, "test@test.com")
        self.assertIsNone(error)

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_badly_formatted_new_user_info_outputs_error(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={  # without 'given_name'
                "family_name": "Mercier",
                "sub": "456",
                "preferred_username": "TROIS",
                "birthdate": "1981-07-27",
                "gender": Usager.GENDER_FEMALE,
                "birthplace": "95277",
                "birthcountry": Usager.BIRTHCOUNTRY_FRANCE,
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response
        usager, error = get_user_info(self.connection)

        self.assertIsNone(usager)
        self.assertIn("The FranceConnect ID is not complete:", error)

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_formatted_new_user_without_birthplace_outputs_usager(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={  # with empty 'birthplace'
                "given_name": "Fabrice",
                "family_name": "Mercier",
                "sub": "456",
                "preferred_username": "TROIS",
                "birthdate": "1981-07-27",
                "gender": Usager.GENDER_MALE,
                "birthplace": "",
                "birthcountry": "99100",
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response

        usager, error = get_user_info(self.connection)

        self.assertEqual(usager.given_name, "Fabrice")
        self.assertIsNone(error)

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_formatted_existing_user_with_email_change_outputs_usager(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(
            return_value={
                "given_name": self.usager.given_name,
                "family_name": self.usager.family_name,
                "sub": self.usager_sub_fc,
                "preferred_username": self.usager.preferred_username,
                "birthdate": self.usager.birthdate,
                "gender": self.usager.gender,
                "birthplace": self.usager.birthplace,
                "birthcountry": self.usager.birthcountry,
                "email": "new@email.com",
            }
        )
        mock_get.return_value = mock_response

        usager, error = get_user_info(self.connection)

        self.assertEqual(usager.id, self.usager.id)
        self.assertEqual(usager.given_name, "Joséphine")
        self.assertEqual(usager.email, "new@email.com")
        self.assertIsNone(error)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "update_email_usager")
