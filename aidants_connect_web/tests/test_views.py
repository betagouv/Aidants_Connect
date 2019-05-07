import os
import json
from secrets import token_urlsafe
from unittest.mock import patch

from django.test.client import Client
from django.test import TestCase
from django.urls import resolve
from django.core.exceptions import ObjectDoesNotExist

from aidants_connect_web.views import home_page, authorize, token, user_info

from aidants_connect_web.models import Connection, User

fc_callback_url = os.getenv("FC_CALLBACK_URL")


class ConnectionModelTest(TestCase):
    def test_saving_and_retrieving_connexion(self):
        first_connexion = Connection()
        first_connexion.state = "aZeRtY"
        first_connexion.code = "ert"
        first_connexion.nonce = "varg"
        first_connexion.save()

        second_connexion = Connection()
        second_connexion.state = "QsDfG"
        second_connexion.save()

        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.state, "aZeRtY")
        self.assertEqual(first_saved_item.nonce, "varg")
        self.assertEqual(second_saved_item.state, "QsDfG")


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

    def test_sending_user_information_triggers_callback(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        response = self.client.post(
            "/authorize/", data={"user_info": "good", "state": "34"}
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


class TokenTests(TestCase):
    def setUp(self):
        self.connection = Connection()
        self.connection.state = "test_state"
        self.connection.code = "test_code"
        self.connection.nonce = "test_nonce"
        self.connection.save()

    def test_token_url_triggers_token_view(self):
        found = resolve("/token/")
        self.assertEqual(found.func, token)

    def test_token_should_respond_when_given_correct_info(self):
        with patch.dict(
            "os.environ",
            {
                "FC_AS_FS_ID": "test_client_id",
                "FC_AS_FS_SECRET": "test_client_secret",
                "FC_CALLBACK_URL": "test_url.test_url",
                "HOST": "localhost",
            },
        ):
            response = self.client.post(
                "/token/",
                {
                    "grant_type": "authorization_code",
                    "redirect_uri": "test_url.test_url/oidc_callback",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "code": "test_code",
                },
            )
            response_content = response.content.decode("utf-8")
            self.assertEqual(response.status_code, 200)
            response_json = json.loads(response_content)
            awaited_response = {
                "access_token": "N5ro73Y2UBpVYLc8xB137A",
                "expires_in": 3600,
                "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJ0ZXN0X2Nsa"
                "WVudF9pZCIsImV4cCI6MTMyNjUxMTg5NCwiaWF0IjoxMzI2NTExMjk0LCJ"
                "pc3MiOiJsb2NhbGhvc3QiLCJzdWIiOiI0MzQ0MzQzNDIzIiwibm9uY2UiO"
                "iJ0ZXN0X25vbmNlIn0.NWhma6Egbxn34v1RVtAd2wQbkCJjAIN0qyNgdKQ"
                "qROA",
                "refresh_token": "5ieq7Bg173y99tT6MA",
                "token_type": "Bearer",
            }

            self.assertEqual(response_json, awaited_response)


class UserInfoTests(TestCase):
    def test_token_url_triggers_token_view(self):
        found = resolve("/userinfo/")
        self.assertEqual(found.func, user_info)


class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")
