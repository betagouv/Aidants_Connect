import os
from django.test import TestCase
from django.urls import resolve
from aidant_connect_web.views import connection, fc_authorize


class HomePageTest(TestCase):

    def test_root_url_resolves_to_connection_view(self):
        found = resolve('/')
        self.assertEqual(found.func, connection)

    def test_root_url_returns_connection_html(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'aidant_connect_web/connection.html')

    def test_fc_button_resolves_to_fc_redirect_view(self):
        found = resolve('/fc_authorize/')
        self.assertEqual(found.func, fc_authorize)

    def test_fc_button_returns_redirect_to_fc(self):
        response = self.client.get('/fc_authorize/')
        base_url = os.getenv('FRANCE_CONNECT_URL')
        franceconnect_client_id = os.getenv('FRANCE_CONNECT_CLIENT_ID')
        franceconnect_callback_uri = f'{os.getenv("HOST")}/callback'
        #scopes = [given_name, family_name, preferred_username, birthdate, gender, birthplace, birthcountry]

        franceconnect_scopes = "openid%20given_name%20family_name%20preferred_username%20birthdate%20gender%20birthplace%20birthcountry"
        franceconnect_state = "customState11"
        franceconnect_nonce = "customNonce11"

        parameters = f"response_type=code&client_id={franceconnect_client_id}&redirect_uri={franceconnect_callback_uri}&scope={franceconnect_scopes}&state={franceconnect_state}&nonce={franceconnect_nonce}"
        expected_url = f"{base_url}/authorize?{parameters}"
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix='',
            fetch_redirect_response=False
        )


class EnvironmentVariableTest(TestCase):

    def test_environment_variables_are_accessible(self):
        SECRET_KEY = os.getenv("TEST")
        self.assertEqual(SECRET_KEY, "Everything is awesome")
