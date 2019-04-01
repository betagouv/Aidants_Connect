from django.test import TestCase
from django.urls import resolve
from aidant_connect_web.views import connection


class HomePageTest(TestCase):

    def test_root_url_resolves_to_connection_view(self):
        found = resolve('/')
        self.assertEqual(found.func, connection)

    def test_root_url_returns_connection_html(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'aidant_connect_web/connection.html')
