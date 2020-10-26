from django.conf import settings
from django.test import tag, TestCase
from aidants_connect_web.views import datapass
from django.urls import resolve


@tag("datapass")
class Datapass(TestCase):
    def setUp(self):
        self.datapass_key = settings.DATAPASS_KEY

    def test_datapass_receiver_url_triggers_the_receiver_view(self):
        found = resolve("/datapass_receiver/")
        self.assertEqual(found.func, datapass.receiver)

    def test_bad_authorization_header_triggers_403(self):
        response = self.client.get(
            "/datapass_receiver/", **{"HTTP_AUTHORIZATION": "bad_token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_good_authorization_header_triggers_200(self):
        response = self.client.get(
            "/datapass_receiver/", **{"HTTP_AUTHORIZATION": "good_token"}
        )
        self.assertEqual(response.status_code, 202)

