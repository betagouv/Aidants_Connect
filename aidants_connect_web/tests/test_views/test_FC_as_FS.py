from datetime import datetime, timedelta
from unittest import mock
from urllib.parse import urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import reverse

import jwt
from freezegun import freeze_time

from aidants_connect_common.constants import AuthorizationDurationChoices
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.models import Connection, Journal, Usager
from aidants_connect_web.tests.factories import AidantFactory, UsagerFactory
from aidants_connect_web.utilities import generate_sha256_hash
from aidants_connect_web.views.FC_as_FS import get_user_info


@tag("new_mandat", "FC_as_FS")
class FCAuthorize(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant = AidantFactory()
        cls.consent_request_id = str(uuid4())

        Connection.objects.create(
            id=1,
            demarches=["argent", "papiers"],
            duree_keyword=AuthorizationDurationChoices.SHORT,
        )

        cls.remote_connection = Connection.objects.create(
            id=2,
            aidant=cls.aidant,
            organisation=cls.aidant.organisation,
            demarches=["argent", "papiers"],
            remote_constent_method=RemoteConsentMethodChoices.SMS.name,
            duree_keyword=AuthorizationDurationChoices.SHORT,
            mandat_is_remote=True,
            user_phone="0 800 840 800",
            consent_request_id=cls.consent_request_id,
        )

    def test_well_formatted_request_fills_connection(self):
        session = self.client.session
        session["connection"] = 1
        session.save()
        self.client.get(reverse("fc_authorize"))
        connection = Connection.objects.get(pk=1)
        self.assertNotEqual(connection.state, "")

    def test_prevent_redirect_on_no_consent(self):
        session = self.client.session
        session["connection"] = 2
        session.save()

        self.client.force_login(self.aidant)

        response = self.client.get(reverse("fc_authorize"))
        self.assertRedirects(response, reverse("new_mandat_waiting_room"))

        Journal.log_user_consents_sms(
            aidant=self.remote_connection.aidant,
            demarche=self.remote_connection.demarche,
            duree=self.remote_connection.duree_keyword,
            remote_constent_method=self.remote_connection.remote_constent_method,
            user_phone=self.remote_connection.user_phone,
            consent_request_id=self.remote_connection.consent_request_id,
            message="Oui",
        )

        self.client.get(reverse("fc_authorize"))
        connection = Connection.objects.get(pk=2)
        self.assertNotEqual(connection.state, "")


DATE = datetime(2019, 1, 14, 3, 20, 34, 0, tzinfo=ZoneInfo("Europe/Paris"))
TEST_FC_CONNECTION_AGE = 300


@tag("new_mandat", "FC_as_FS")
@override_settings(FC_CONNECTION_AGE=TEST_FC_CONNECTION_AGE)
class FCCallback(TestCase):
    date = DATE

    @freeze_time(date)
    def setUp(self):
        self.client = Client()
        self.aidant = AidantFactory()
        self.client.force_login(self.aidant)
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
            organisation=self.aidant.organisation,
        )
        self.connection2 = Connection.objects.create(
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
    def test_no_code_triggers_fc_error(self):
        response = self.client.get("/callback/", data={"state": self.connection.state})
        self.check_fc_error_with_message(response, self.connection.pk)

    @freeze_time(date)
    def test_no_state_triggers_fc_error(self):
        response = self.client.get("/callback/", data={"code": "test_code"})
        self.check_fc_error_with_message(response)

    @freeze_time(date)
    def test_non_existing_state_triggers_fc_error(self):
        response = self.client.get(
            "/callback/", data={"state": "wrong_state", "code": "test_code"}
        )
        self.check_fc_error_with_message(response)

    date_expired = DATE + timedelta(seconds=TEST_FC_CONNECTION_AGE + 1)

    def check_fc_error_with_message(self, response, connection_id=None):
        query_params = (
            f"?{urlencode({'connection_id': connection_id})}" if connection_id else ""
        )

        self.assertRedirects(
            response,
            f"{reverse('new_mandat')}{query_params}",
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("new_mandat"))
        self.assertContains(response, "Nous avons rencontré une erreur")

    @freeze_time(date_expired)
    def test_expired_connection_yields_fc_error(self):
        response = self.client.get(
            "/callback/", data={"state": self.connection.state, "code": "test_code"}
        )
        self.check_fc_error_with_message(response, self.connection.pk)

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
            "/callback/", data={"state": self.connection2.state, "code": "test_code"}
        )
        self.check_fc_error_with_message(response, self.connection2.pk)

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

        id_token = jwt.encode(id_token, settings.FC_AS_FS_SECRET, algorithm="HS256")

        mock_response.json = mock.Mock(
            return_value={
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 60,
                "id_token": id_token,
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
        parameters = urlencode(
            {
                "id_token_hint": id_token,
                "state": "test_state",
                "post_logout_redirect_uri": (
                    f"{settings.FC_AS_FS_CALLBACK_URL}{reverse('logout_callback')}"
                ),
            }
        )
        url = f"https://fcp.integ01.dev-franceconnect.fr/api/v1/logout?{parameters}"
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

        encoded_token = jwt.encode(
            id_token, settings.FC_AS_FS_SECRET, algorithm="HS256"
        )

        mock_response.json = mock.Mock(
            return_value={
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 60,
                "id_token": encoded_token,
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

        parameters = urlencode(
            {
                "id_token_hint": encoded_token,
                "state": "test_state",
                "post_logout_redirect_uri": (
                    f"{settings.FC_AS_FS_CALLBACK_URL}{reverse('logout_callback')}"
                ),
            }
        )
        url = f"https://fcp.integ01.dev-franceconnect.fr/api/v1/logout?{parameters}"
        self.assertRedirects(response, url, fetch_redirect_response=False)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "franceconnect_usager")


@tag("new_mandat", "FC_as_FS")
class GetUserInfoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usager_sub_fc = "123"
        cls.usager_sub = generate_sha256_hash(
            f"{cls.usager_sub_fc}{settings.FC_AS_FI_HASH_SALT}".encode()
        )
        cls.usager = UsagerFactory(given_name="Joséphine", sub=cls.usager_sub)
        cls.aidant = AidantFactory()
        cls.connection = Connection.objects.create(
            access_token="mock_access_token",
            aidant=cls.aidant,
            organisation=cls.aidant.organisation,
        )
        cls.connection_with_phone = Connection.objects.create(
            access_token="mock_access_token_with_phone",
            aidant=cls.aidant,
            organisation=cls.aidant.organisation,
            user_phone="0 800 840 800",
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
        self.assertEqual(usager.preferred_username, "TROIS")
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
    def test_empty_response_does_not_fail_badly(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = "content"
        mock_response.json = mock.Mock(return_value={})
        mock_get.return_value = mock_response
        usager, error = get_user_info(self.connection)

        self.assertIsNone(usager)
        self.assertIn("Unable to find sub in FC user info", error)

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
                "preferred_username": "TROIS",
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
        self.assertEqual(usager.preferred_username, "TROIS")
        self.assertEqual(usager.email, "new@email.com")
        self.assertIsNone(error)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "update_email_usager")

    @mock.patch("aidants_connect_web.views.FC_as_FS.python_request.get")
    def test_formatted_existing_user_with_phone_change_outputs_usager(self, mock_get):
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
                "email": "test@test.com",
            }
        )
        mock_get.return_value = mock_response

        usager, error = get_user_info(self.connection_with_phone)

        self.assertEqual(usager.id, self.usager.id)
        self.assertEqual(usager.given_name, "Joséphine")
        self.assertEqual(usager.phone, "0 800 840 800")
        self.assertIsNone(error)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "update_phone_usager")
