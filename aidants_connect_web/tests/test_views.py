import os
import json
import mock
import jwt
from pytz import timezone
from secrets import token_urlsafe
from datetime import date, datetime, timedelta
from freezegun import freeze_time

from django.test.client import Client
from django.test import TestCase, override_settings
from django.urls import resolve
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.messages import get_messages
from django.urls import reverse

from aidants_connect_web.forms import MandatForm
from aidants_connect_web.views import (
    home_page,
    authorize,
    token,
    user_info,
    logout_page,
    recap,
    fi_select_demarche,
)
from aidants_connect_web.models import (
    Connection,
    User,
    Usager,
    Mandat,
    CONNECTION_EXPIRATION_TIME,
)

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


class HomePageTests(TestCase):
    def test_root_url_triggers_the_homepage_view(self):
        found = resolve("/")
        self.assertEqual(found.func, home_page)

    def test_root_url_triggers_the_homepage_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "aidants_connect_web/home_page.html")


class LogoutPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )

    def test_logout_url_triggers_the_logout_view(self):
        found = resolve("/logout/")
        self.assertEqual(found.func, logout_page)

    def test_logout_url_triggers_loging_if_not_logged_in(self):
        response = self.client.get("/logout/")
        self.assertRedirects(response, "/accounts/login/?next=/logout/")

    def test_logout_url_triggers_home_page_if_logged_in(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        response = self.client.get("/logout/")
        self.assertRedirects(response, "/")


class RecapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )

    def test_recap_url_triggers_the_recap_view(self):
        found = resolve("/recap/")
        self.assertEqual(found.func, recap)

    def test_recap_url_triggers_the_recap_template(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "sub": "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "female",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        mandat_form = MandatForm(
            data={"perimeter": ["chg_adresse", "heberg_social"], "duration": 3}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()

        response = self.client.get("/recap/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/mandat/recap.html")
        self.assertEqual(Usager.objects.all().count(), 0)

    def test_post_to_recap_with_correct_data_redirects_to_dashboard(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "sub": "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "F",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        mandat_form = MandatForm(
            data={"perimeter": ["chg_adresse", "heberg_social"], "duration": 3}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()

        response = self.client.post(
            "/recap/", data={"personal_data": True, "brief": True}
        )
        self.assertEqual(Usager.objects.all().count(), 1)
        usager = Usager.objects.get(given_name="Fabrice")
        self.assertEqual(
            usager.sub,
            "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )
        self.assertEqual(usager.birthplace, 95277)
        self.assertRedirects(response, "/dashboard/")

    def test_post_to_recap_without_sub_creates_error(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "F",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        mandat_form = MandatForm(
            data={"perimeter": ["chg_adresse", "heberg_social"], "duration": 3}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()
        response = self.client.post(
            "/recap/", data={"personal_data": True, "brief": True}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)


class AuthorizeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
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
        )

    def test_authorize_url_triggers_the_authorize_view(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        found = resolve("/authorize/")
        self.assertEqual(found.func, authorize)

    def test_authorize_url_without_arguments_returns_403(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        response = self.client.get("/authorize/")
        self.assertEqual(response.status_code, 403)

    def test_authorize_url_triggers_the_authorize_template(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        fc_call_state = token_urlsafe(4)
        fc_call_nonce = token_urlsafe(4)
        fc_response_type = "code"
        fc_client_id = "FranceConnectInteg"
        fc_redirect_uri = (
            "https%3A%2F%2Ffcp.integ01.dev-franceconnect.fr%2Foidc_callback"
        )
        fc_scopes = "openid profile email address phone birth"
        fc_acr_values = "eidas1"

        response = self.client.get(
            "/authorize/",
            data={
                "state": fc_call_state,
                "nonce": fc_call_nonce,
                "response_type": fc_response_type,
                "client_id": fc_client_id,
                "redirect_uri": fc_redirect_uri,
                "scope": fc_scopes,
                "acr_values": fc_acr_values,
            },
        )

        self.assertTemplateUsed(response, "aidants_connect_web/authorize.html")

    def test_sending_user_information_triggers_callback(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        c = Connection()
        c.state = "test_state"
        c.code = "test_code"
        c.nonce = "test_nonce"
        c.sub_usager = "test_sub"
        c.save()
        usager_id = self.usager.id
        response = self.client.post(
            "/authorize/", data={"state": "test_state", "chosen_user": usager_id}
        )
        try:
            saved_items = Connection.objects.all()
        except ObjectDoesNotExist:
            raise AttributeError
        self.assertEqual(saved_items.count(), 1)
        connection = saved_items[0]
        state = connection.state
        self.assertEqual(connection.sub_usager, "123")
        self.assertNotEqual(connection.nonce, "No Nonce Provided")

        url = reverse("fi_select_demarche") + "?state=" + state
        self.assertRedirects(response, url, fetch_redirect_response=False)


class FISelectDemarcheTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
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
        )
        self.usager2 = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate="1969-12-15",
            gender="female",
            birthplace="70447",
            birthcountry="99100",
            sub="123",
            email="User@user.domain",
        )
        self.connection = Connection.objects.create(
            state="test_state", code="test_code", nonce="test_nonce", sub_usager="123"
        )
        self.mandat = Mandat.objects.create(
            aidant=self.user,
            usager=self.usager,
            perimeter=["naissance", "aspa"],
            duration=6,
        )

        self.mandat_2 = Mandat.objects.create(
            aidant=self.user, usager=self.usager, perimeter=["carte_grise"], duration=3
        )

        self.mandat_3 = Mandat.objects.create(
            aidant=self.user, usager=self.usager, perimeter=["aspa"], duration=3
        )

    def test_FI_select_demarche_url_triggers_the_fi_select_demarche_view(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        found = resolve("/select_demarche/")
        self.assertEqual(found.func, fi_select_demarche)

    def test_FI_select_demarche_triggers_FI_select_demarche_template(self):
        self.client.login(username="Thierry", password="motdepassedethierry")

        response = self.client.get("/select_demarche/", data={"state": "test_state"})

        self.assertTemplateUsed(response, "aidants_connect_web/fi_select_demarche.html")

    def test_get_perimeters_for_one_usager_and_two_mandats(self):
        self.client.login(username="Thierry", password="motdepassedethierry")

        response = self.client.get("/select_demarche/", data={"state": "test_state"})
        self.assertEqual(
            response.context["demarches"], {"naissance", "aspa", "carte_grise"}
        )

    # TODO test that a POST triggers a redirect to f"{fc_callback_url}?code={
    #  code}&state={state}"


@override_settings(
    FC_AS_FI_ID="test_client_id",
    FC_AS_FI_SECRET="test_client_secret",
    FC_AS_FI_CALLBACK_URL="test_url.test_url",
    HOST="localhost",
)
class TokenTests(TestCase):
    def setUp(self):
        self.connection = Connection()
        self.connection.state = "test_state"
        self.connection.code = "test_code"
        self.connection.nonce = "test_nonce"
        self.connection.sub_usager = "test_sub"
        self.connection.expiresOn = datetime(
            2012, 1, 14, 3, 21, 34, tzinfo=timezone("Europe/Paris")
        )
        self.connection.save()
        self.fc_request = {
            "grant_type": "authorization_code",
            "redirect_uri": "test_url.test_url",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "code": "test_code",
        }

    def test_token_url_triggers_token_view(self):
        found = resolve("/token/")
        self.assertEqual(found.func, token)

    date = datetime(2012, 1, 14, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris"))

    @freeze_time(date)
    def test_correct_info_triggers_200(self):

        response = self.client.post("/token/", self.fc_request)

        response_content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response_content)
        connection = Connection.objects.get(code="test_code")
        awaited_response = {
            "access_token": connection.access_token,
            "expires_in": 3600,
            "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJ0ZXN0X2NsaWVud"
            "F9pZCIsImV4cCI6MTMyNjUxMTI5NCwiaWF0IjoxMzI2NTEwNjk0LCJpc3MiOiJ"
            "sb2NhbGhvc3QiLCJzdWIiOiJ0ZXN0X3N1YiIsIm5vbmNlIjoidGVzdF9ub25jZ"
            "SJ9.aYSfYJK_Lml15DY7MuhrUBI1wja70WBfeyKqiUBMLlE",
            "refresh_token": "5ieq7Bg173y99tT6MA",
            "token_type": "Bearer",
        }

        self.assertEqual(response_json, awaited_response)

    def test_wrong_grant_type_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["grant_type"] = "not_authorization_code"
        response = self.client.post("/token/", fc_request)
        self.assertEqual(response.status_code, 403)

    def test_wrong_redirect_uri_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["redirect_uri"] = "test_url.test_url/wrong_uri"

        response = self.client.post("/token/", fc_request)
        self.assertEqual(response.status_code, 403)

    def test_wrong_client_id_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["client_id"] = "wrong_client_id"
        response = self.client.post("/token/", fc_request)
        self.assertEqual(response.status_code, 403)

    def test_wrong_client_secret_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["client_secret"] = "wrong_client_secret"
        response = self.client.post("/token/", fc_request)
        self.assertEqual(response.status_code, 403)

    def test_wrong_code_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["code"] = "wrong_code"
        response = self.client.post("/token/", fc_request)
        self.assertEqual(response.status_code, 403)

    date_expired = date + timedelta(minutes=CONNECTION_EXPIRATION_TIME + 20)

    @freeze_time(date_expired)
    def test_expired_code_triggers_403(self):
        response = self.client.post("/token/", self.fc_request)
        self.assertEqual(response.status_code, 403)


class UserInfoTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.connection = Connection()
        self.connection.state = "test_state"
        self.connection.code = "test_code"
        self.connection.nonce = "test_nonce"
        self.connection.sub_usager = "test_sub"
        self.connection.access_token = "test_access_token"
        self.connection.expiresOn = datetime(
            2012, 1, 14, 3, 21, 34, 0, tzinfo=timezone("Europe/Paris")
        )
        self.connection.save()

        self.usager = Usager()
        self.usager.given_name = "Joséphine"
        self.usager.family_name = "ST-PIERRE"
        self.usager.preferred_username = "ST-PIERRE"
        self.usager.birthdate = date(1969, 12, 25)
        self.usager.gender = "F"
        self.usager.birthplace = 70447
        self.usager.birthcountry = 99100
        self.usager.sub = "test_sub"
        self.usager.email = "User@user.domain"
        self.usager.save()

    def test_token_url_triggers_token_view(self):
        found = resolve("/userinfo/")
        self.assertEqual(found.func, user_info)

    date = datetime(2012, 1, 14, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris"))

    @freeze_time(date)
    def test_well_formatted_access_token_returns_200(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "Bearer test_access_token"}
        )

        FC_formated_info = {
            "given_name": "Joséphine",
            "family_name": "ST-PIERRE",
            "preferred_username": "ST-PIERRE",
            "birthdate": "1969-12-25",
            "gender": "F",
            "birthplace": "70447",
            "birthcountry": "99100",
            "sub": "test_sub",
            "email": "User@user.domain",
        }

        content = response.json()

        self.assertEqual(content, FC_formated_info)

    date_expired = date + timedelta(minutes=CONNECTION_EXPIRATION_TIME + 20)

    @freeze_time(date_expired)
    def test_expired_access_token_returns_403(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "Bearer test_access_token"}
        )

        self.assertEqual(response.status_code, 403)

    def test_badly_formatted_authorization_header_triggers_403(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "test_access_token"}
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "Bearer: test_access_token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_token_triggers_403(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "wrong_access_token"}
        )
        self.assertEqual(response.status_code, 403)


class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")


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
