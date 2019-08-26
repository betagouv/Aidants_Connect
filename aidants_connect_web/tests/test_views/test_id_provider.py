import json
from pytz import timezone
from secrets import token_urlsafe
from datetime import date, datetime, timedelta
from freezegun import freeze_time

from django.db.models.query import QuerySet
from django.test.client import Client
from django.test import TestCase, override_settings, tag
from django.urls import resolve
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.urls import reverse

from aidants_connect_web.views import id_provider
from aidants_connect_web.models import (
    Connection,
    Aidant,
    Usager,
    Mandat,
    CONNECTION_EXPIRATION_TIME,
    Journal,
)

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("id_provider")
class AuthorizeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = Aidant.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )
        Aidant.objects.create_user(
            "Jacques", "jacques@domain.user", "motdepassedejacques"
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
        Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="123"),
            perimeter=["Revenus"],
            duration=6,
        )

        Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="123"),
            perimeter=["Famille"],
            duration=12,
        )

        Mandat.objects.create(
            aidant=Aidant.objects.get(username="Jacques"),
            usager=Usager.objects.get(sub="123"),
            perimeter=["Logement"],
            duration=12,
        )

    def test_authorize_url_triggers_the_authorize_view(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        found = resolve("/authorize/")
        self.assertEqual(found.func, id_provider.authorize)

    def test_authorize_url_without_arguments_returns_403(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        response = self.client.get("/authorize/")
        self.assertEqual(response.status_code, 403)

    def test_authorize_url_triggers_the_authorize_template(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        fc_call_state = token_urlsafe(4)
        # fc_call_nonce = token_urlsafe(4)
        # fc_response_type = "code"
        # fc_client_id = "FranceConnectInteg"
        # fc_redirect_uri = (
        #     "https%3A%2F%2Ffcp.integ01.dev-franceconnect.fr%2Foidc_callback"
        # )
        # fc_scopes = "openid profile email address phone birth"
        # fc_acr_values = "eidas1"

        response = self.client.get(
            "/authorize/",
            data={
                "state": fc_call_state,
                # "nonce": fc_call_nonce,
                # "response_type": fc_response_type,
                # "client_id": fc_client_id,
                # "redirect_uri": fc_redirect_uri,
                # "scope": fc_scopes,
                # "acr_values": fc_acr_values,
            },
        )

        self.assertTemplateUsed(
            response, "aidants_connect_web/id_provider/authorize.html"
        )

    def test_authorize_sends_the_correct_amount_of_usagers(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        fc_call_state = token_urlsafe(4)

        response = self.client.get("/authorize/", data={"state": fc_call_state})

        self.assertIsInstance(response.context["state"], str)
        self.assertIsInstance(response.context["usagers"], QuerySet)
        self.assertEqual(len(response.context["usagers"]), 1)
        self.assertIsInstance(response.context["aidant"], Aidant)

    @tag("this")
    def test_sending_user_information_triggers_callback(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        c = Connection.objects.create(
            state="test_state", code="test_code", nonce="test_nonce", usager=self.usager
        )
        usager_id = c.usager.id
        response = self.client.post(
            "/authorize/", data={"state": "test_state", "chosen_usager": usager_id}
        )
        try:
            saved_items = Connection.objects.all()
        except ObjectDoesNotExist:
            raise AttributeError
        self.assertEqual(saved_items.count(), 1)
        connection = saved_items[0]
        state = connection.state
        self.assertEqual(connection.usager.sub, "123")
        self.assertNotEqual(connection.nonce, "No Nonce Provided")

        url = reverse("fi_select_demarche") + "?state=" + state
        self.assertRedirects(response, url, fetch_redirect_response=False)


@tag("id_provider")
class FISelectDemarcheTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = Aidant.objects.create_user(
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
            given_name="Fabrice",
            family_name="MERCIER",
            preferred_username="TROIS",
            birthdate="1981-07-27",
            gender="male",
            birthplace="70447",
            birthcountry="99100",
            sub="124",
            email="User@user.domain",
        )
        self.connection = Connection.objects.create(
            state="test_state", code="test_code", nonce="test_nonce", usager=self.usager
        )
        self.mandat = Mandat.objects.create(
            aidant=self.aidant,
            usager=self.usager,
            perimeter=["transports", "logement"],
            duration=6,
        )

        self.mandat_2 = Mandat.objects.create(
            aidant=self.aidant, usager=self.usager, perimeter=["famille"], duration=3
        )

        self.mandat_3 = Mandat.objects.create(
            aidant=self.aidant, usager=self.usager2, perimeter=["aspa"], duration=3
        )

    def test_FI_select_demarche_url_triggers_the_fi_select_demarche_view(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        found = resolve("/select_demarche/")
        self.assertEqual(found.func, id_provider.fi_select_demarche)

    def test_FI_select_demarche_triggers_FI_select_demarche_template(self):
        self.client.login(username="Thierry", password="motdepassedethierry")

        response = self.client.get("/select_demarche/", data={"state": "test_state"})

        self.assertTemplateUsed(
            response, "aidants_connect_web/id_provider/fi_select_demarche.html"
        )

    def test_get_perimeters_for_one_usager_and_two_mandats(self):
        self.client.login(username="Thierry", password="motdepassedethierry")

        response = self.client.get("/select_demarche/", data={"state": "test_state"})
        mandats = [key for key, value in response.context["demarches"].items()]
        self.assertEqual(mandats, ["transports", "logement", "famille"])

    # TODO test that a POST triggers a redirect to f"{fc_callback_url}?code={
    #  code}&state={state}"


@tag("id_provider")
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
        self.connection.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate="1969-12-15",
            gender="female",
            birthplace="70447",
            birthcountry="99100",
            sub="test_sub",
            email="User@user.domain",
        )
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
        self.assertEqual(found.func, id_provider.token)

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


@tag("id_provider")
class UserInfoTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate=date(1969, 12, 25),
            gender="F",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub",
            email="User@user.domain",
            creation_date="2019-08-05T15:49:13.972Z",
        )

        self.usager_2 = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate=date(1969, 12, 25),
            gender="F",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub2",
            email="User@user.domain",
            creation_date="2019-08-05T15:49:13.972Z",
        )

        self.connection = Connection.objects.create(
            state="test_state",
            code="test_code",
            nonce="test_nonce",
            usager=self.usager,
            access_token="test_access_token",
            expiresOn=datetime(
                2012, 1, 14, 3, 21, 34, 0, tzinfo=timezone("Europe/Paris")
            ),
        )
        self.aidant = Aidant.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )

    def test_token_url_triggers_token_view(self):
        found = resolve("/userinfo/")
        self.assertEqual(found.func, id_provider.user_info)

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
            "creation_date": "2019-08-05T15:49:13.972Z",
        }

        content = response.json()

        self.assertEqual(content, FC_formated_info)

    @freeze_time(date)
    def test_mandat_use_triggers_journal_entry(self):
        self.client.login(username="Thierry", password="motdepassedethierry")

        self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "Bearer test_access_token"}
        )

        journal_entries = Journal.objects.all().order_by("creation_date")
        self.assertEqual(journal_entries.count(), 2)
        self.assertEqual(journal_entries[1].action, "use_mandat")

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
