import os
import json
from secrets import token_urlsafe
from unittest.mock import patch
from datetime import date
from freezegun import freeze_time

from django.test.client import Client
from django.test import TestCase, override_settings
from django.urls import resolve
from django.core.exceptions import ObjectDoesNotExist

from aidants_connect_web.views import home_page, authorize, token, user_info
from aidants_connect_web.forms import UsagerForm
from aidants_connect_web.models import Connection, User, Usager

fc_callback_url = os.getenv("FC_CALLBACK_URL")


class homePageTests(TestCase):
    def test_root_url_triggers_the_homepage_view(self):
        found = resolve("/")
        self.assertEqual(found.func, home_page)

    def test_root_url_triggers_the_homepage_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "aidants_connect_web/home_page.html")


class AuthorizeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
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

    def test_authorize_page_uses_item_form(self):
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
        self.assertIsInstance(response.context["form"], UsagerForm)

    def test_sending_user_information_triggers_callback(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        connection = Connection()
        connection.state = "test_state"
        connection.code = "test_code"
        connection.nonce = "test_nonce"
        connection.sub = "test_sub"
        connection.save()

        response = self.client.post(
            "/authorize/",
            data={
                "state": "test_state",
                "given_name": "Joséphine",
                "family_name": "ST-PIERRE",
                "preferred_username": "ST-PIERRE",
                "birthdate": "1969-12-15",
                "gender": "F",
                "birthplace": "70447",
                "birthcountry": "99100",
                "sub": "123",
                "email": "User@user.domain",
            },
        )
        try:
            saved_items = Connection.objects.all()
        except ObjectDoesNotExist:
            raise AttributeError
        self.assertEqual(saved_items.count(), 1)
        code = saved_items[0].code
        state = saved_items[0].state
        self.assertNotEqual(saved_items[0].nonce, "No Nonce Provided")
        url = f"{fc_callback_url}?code={code}&state={state}"
        self.assertRedirects(response, url, fetch_redirect_response=False)


@override_settings(
        FC_AS_FS_ID="test_client_id",
        FC_AS_FS_SECRET="test_client_secret",
        FC_CALLBACK_URL="test_url.test_url",
        HOST="localhost"
    )
class TokenTests(TestCase):

    def setUp(self):
        self.connection = Connection()
        self.connection.state = "test_state"
        self.connection.code = "test_code"
        self.connection.nonce = "test_nonce"
        self.connection.sub_usager = "test_sub"
        self.connection.save()
        self.fc_request = {
                    "grant_type": "authorization_code",
                    "redirect_uri": "test_url.test_url/oidc_callback",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "code": "test_code",
                }

    def test_token_url_triggers_token_view(self):
        found = resolve("/token/")
        self.assertEqual(found.func, token)

    @freeze_time("2012-01-14 03:21:34", tz_offset=2)
    def test_correct_info_triggers_200(self):
        response = self.client.post(
                "/token/", self.fc_request
            )

        response_content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response_content)
        connection = Connection.objects.get(code="test_code")
        awaited_response = {
            "access_token": connection.access_token,
            "expires_in": 3600,
            "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJ0ZXN0X2Nsa"
                        "WVudF9pZCIsImV4cCI6MTMyNjUxMTg5NCwiaWF0IjoxMzI2NTExMjk0LCJ"
                        "pc3MiOiJsb2NhbGhvc3QiLCJzdWIiOiJ0ZXN0X3N1YiIsIm5vbmNl"
                        "IjoidGVzdF9ub25jZSJ9.VeupzW4ejtdGl2oAgOalfFGdAnxlc66G"
                        "SIzu3T3Ob7s",
            "refresh_token": "5ieq7Bg173y99tT6MA",
            "token_type": "Bearer",
        }

        self.assertEqual(response_json, awaited_response)

    def test_wrong_grant_type_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["grant_type"] = "not_authorization_code"
        response = self.client.post(
            "/token/", fc_request
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_redirect_uri_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["redirect_uri"] = "test_url.test_url/wrong_uri"

        response = self.client.post(
            "/token/", fc_request
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_client_id_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["client_id"] = "wrong_client_id"
        response = self.client.post(
            "/token/", fc_request
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_client_secret_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["client_secret"] = "wrong_client_secret"
        response = self.client.post(
            "/token/", fc_request
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_code_triggers_403(self):
        fc_request = dict(self.fc_request)
        fc_request["code"] = "wrong_code"
        response = self.client.post(
            "/token/", fc_request
        )
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

    def test_user_info_is_given_when_access_token_is_right(self):
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

    def test_user_info_returns_403_when_authorization_is_badly_formated(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "test_access_token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_user_info_returns_403_when_authorization_has_wrong_token(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "wrong_access_token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_user_info_returns_403_when_authorization_has_wrong_intro(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "Bearer: test_access_token"}
        )
        self.assertEqual(response.status_code, 403)


class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")
