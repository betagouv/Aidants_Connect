import os
from django.test import TestCase
from django.urls import resolve
from aidant_connect_web.views import connection, fc_authorize, fc_callback, switchboard


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
        scopes = [
          'given_name',
          'family_name',
          'preferred_username',
          'birthdate',
          'gender',
          'birthplace',
          'birthcountry'
          ]

        franceconnect_scopes =  \
            f'openid{"".join(["%20" + scope for scope in scopes])}'
        franceconnect_state = "customState11"
        franceconnect_nonce = "customNonce11"

        parameters = \
            f"response_type=code" \
            f"&client_id={franceconnect_client_id}" \
            f"&redirect_uri={franceconnect_callback_uri}" \
            f"&scope={franceconnect_scopes}" \
            f"&state={franceconnect_state}" \
            f"&nonce={franceconnect_nonce}"

        expected_url = f"{base_url}/authorize?{parameters}"
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix='',
            fetch_redirect_response=False
        )

    def test_fc_callback_resolves_to_fc_callback_view(self):
        found = resolve('/callback/')
        self.assertEqual(found.func, fc_callback)

    def test_fc_process_redirects_switchboard_html(self):
        response = self.client.get('/callback/')
        self.assertRedirects(
            response,
            '/switchboard/',
            status_code=302,
            target_status_code=200,
            msg_prefix='',
            fetch_redirect_response=True
        )

    def test_switchboard_resolves_to_switchboard_view(self):
        found = resolve('/switchboard/')
        self.assertEqual(found.func, switchboard)


class SwitchBoardTestNotConnected(TestCase):

    def setUp(self):
        session = self.client.session
        session['user_info'] = None
        session.save()
    def test_switchboard_url_returns_switchboard_html_when_connected(self):
        response = self.client.get('/switchboard/')

        self.assertTemplateUsed(response, 'aidant_connect_web/connection.html')


class SwitchBoardTestConnected(TestCase):

    def setUp(self):
        session = self.client.session
        session['user_info'] = {
            'given_name': "Melanie"
        }
        session.save()

    def test_switchboard_url_returns_switchboard_html_when_connected(self):
        response = self.client.get('/switchboard/')

        self.assertTemplateUsed(response, 'aidant_connect_web/switchboard.html')


class EnvironmentVariableTest(TestCase):

    def test_environment_variables_are_accessible(self):
        secret_key = os.getenv("TEST")
        self.assertEqual(secret_key, "Everything is awesome")
