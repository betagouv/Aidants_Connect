import os
from secrets import token_urlsafe

from django.test.client import Client
from django.test import TestCase
from django.urls import resolve

from aidant_connect_web.views import authorize, token
from aidant_connect_web.models import Connection, User

fc_callback_url = os.getenv("FC_CALLBACK_URL")


class ConnectionModelTest(TestCase):
    def test_saving_and_retrieving_connexion(self):
        first_connexion = Connection()
        first_connexion.state = "aZeRtY"
        first_connexion.save()

        second_connexion = Connection()
        second_connexion.state = "QsDfG"
        second_connexion.save()

        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.state, "aZeRtY")
        self.assertEqual(second_saved_item.state, "QsDfG")


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
        fc_call_state = token_urlsafe(64)
        fc_call_nounce = token_urlsafe(64)
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
                "nonce": fc_call_nounce,
                "response_type": fc_response_type,
                "client_id": fc_client_id,
                "redirect_uri": fc_redirect_uri,
                "scope": fc_scopes,
                "acr_values": fc_acr_values,
            },
        )

        self.assertTemplateUsed(response, "aidant_connect_web/authorize.html")

    def test_sending_user_information_triggers_callback(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        response = self.client.post(
            "/authorize/", data={"user_info": "good", "state": "34"}
        )
        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 1)
        code = saved_items[0].code
        state = saved_items[0].state
        url = f"{fc_callback_url}?code={code}&state={state}"
        self.assertRedirects(response, url, fetch_redirect_response=False)


class TokenTests(TestCase):
    def test_token_url_triggers_token_view(self):
        found = resolve("/token/")
        self.assertEqual(found.func, token)


class EnvironmentVariableTest(TestCase):
    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")
