from django.test import TestCase
from django.urls import resolve
from aidant_connect_web.views import connection


class HomePageTest(TestCase):

    def test_root_url_resolves_to_home_page_view(self):
        found = resolve('/')
        self.assertEqual(found.func, connection)
