from datetime import date, datetime, timedelta
import json

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db.models.query import QuerySet
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils import timezone

from freezegun import freeze_time
from pytz import timezone as pytz_timezone

from aidants_connect_web.models import (
    Aidant,
    Connection,
    Journal,
    Usager,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.views import id_provider


@tag("id_provider")
class AuthorizeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = AidantFactory()
        self.aidant_jacques = AidantFactory(
            username="jacques@domain.user", email="jacques@domain.user"
        )
        self.usager = UsagerFactory(given_name="Joséphine", sub="123")

        mandat_1 = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=6),
        )

        AutorisationFactory(
            mandat=mandat_1,
            demarche="Revenus",
            revocation_date=timezone.now() - timedelta(days=1),
        )

        mandat_2 = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=12),
        )

        AutorisationFactory(
            mandat=mandat_2, demarche="Famille",
        )
        AutorisationFactory(
            mandat=mandat_2, demarche="Revenus",
        )

        mandat_3 = MandatFactory(
            organisation=self.aidant_jacques.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=mandat_3, demarche="Logement",
        )
        date_further_away_minus_one_hour = datetime(
            2019, 1, 9, 8, tzinfo=pytz_timezone("Europe/Paris")
        )
        self.connection = Connection.objects.create(
            state="test_expiration_date_triggered",
            nonce="avalidnonce456",
            usager=self.usager,
            expires_on=date_further_away_minus_one_hour,
        )

    def test_authorize_url_triggers_the_authorize_view(self):
        self.client.force_login(self.aidant_thierry)
        found = resolve("/authorize/")
        self.assertEqual(found.func, id_provider.authorize)

    def test_authorize_url_without_arguments_returns_400(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/authorize/")
        self.assertEqual(response.status_code, 400)

    def test_authorize_url_triggers_the_authorize_template(self):
        self.client.force_login(self.aidant_thierry)

        good_data = {
            "state": "avalidstate123",
            "nonce": "avalidnonce456",
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            "scope": "openid profile email address phone birth",
            "acr_values": "eidas1",
        }

        response = self.client.get("/authorize/", data=good_data)

        self.assertTemplateUsed(
            response, "aidants_connect_web/id_provider/authorize.html"
        )

        self.assertEqual(response.status_code, 200)

    def test_authorize_url_without_right_parameters_triggers_bad_request(self):
        self.client.force_login(self.aidant_thierry)

        good_data = {
            "state": "avalidstate123",
            "nonce": "avalidnonce456",
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            "scope": "openid profile email address phone birth",
            "acr_values": "eidas1",
        }

        for data, value in good_data.items():
            data_with_missing_item = good_data.copy()
            del data_with_missing_item[data]

            response = self.client.get("/authorize/", data=data_with_missing_item)

            self.assertEqual(response.status_code, 400)

    def test_authorize_url_with_malformed_parameters_triggers_403(self):
        self.client.force_login(self.aidant_thierry)

        dynamic_data = {"state": "avalidstate123", "nonce": "avalidnonce456"}
        good_static_data = {
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            "scope": "openid profile email address phone birth",
            "acr_values": "eidas1",
        }

        for data, value in dynamic_data.items():
            dynamic_data_with_wrong_item = dynamic_data.copy()
            dynamic_data_with_wrong_item[data] = "aninvalidvalue 123"

            sent_data = {**dynamic_data_with_wrong_item, **good_static_data}
            response = self.client.get("/authorize/", data=sent_data)

            self.assertEqual(response.status_code, 403)

    def test_authorize_url_with_wrong_parameters_triggers_403(self):
        self.client.force_login(self.aidant_thierry)

        dynamic_data = {"state": "avalidstate123", "nonce": "avalidnonce456"}
        good_static_data = {
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            "scope": "openid profile email address phone birth",
            "acr_values": "eidas1",
        }

        for data, value in good_static_data.items():
            static_data_with_wrong_item = good_static_data.copy()
            static_data_with_wrong_item[data] = "wrong_data"

            sent_data = {**dynamic_data, **static_data_with_wrong_item}
            response = self.client.get("/authorize/", data=sent_data)

            self.assertEqual(response.status_code, 403)

    def test_authorize_sends_the_correct_amount_of_usagers(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.get(
            "/authorize/",
            data={
                "state": "avalidstate123",
                "nonce": "avalidnonce456",
                "response_type": "code",
                "client_id": settings.FC_AS_FI_ID,
                "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
                "scope": "openid profile email address phone birth",
                "acr_values": "eidas1",
            },
        )

        self.assertIsInstance(response.context["connection_id"], int)
        self.assertIsInstance(response.context["usagers"], QuerySet)
        self.assertEqual(len(response.context["usagers"]), 1)
        self.assertIsInstance(response.context["aidant"], Aidant)

    def test_sending_user_information_triggers_callback(self):
        self.client.force_login(self.aidant_thierry)

        connection = Connection.objects.create(
            state="avalidstate123", nonce="avalidnonce456", usager=self.usager
        )

        response = self.client.post(
            "/authorize/",
            data={
                "connection_id": connection.id,
                "chosen_usager": connection.usager.id,
            },
        )

        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 2)
        connection = saved_items[1]
        self.assertEqual(connection.usager.sub, "123")
        self.assertNotEqual(connection.nonce, "No Nonce Provided")

        url = reverse("fi_select_demarche") + "?connection_id=" + str(connection.id)
        self.assertRedirects(response, url, fetch_redirect_response=False)

    date_further_away = datetime(2019, 1, 9, 9, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(date_further_away)
    def test_post_to_authorize_with_expired_connection_triggers_connection_timeout(
        self,
    ):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={"connection_id": self.connection.id, "chosen_usager": 1},
        )
        self.assertEqual(response.status_code, 408)

    def test_post_to_authorize_with_unknown_connection_triggers_forbidden(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={"connection_id": (self.connection.id + 1), "chosen_usager": 1},
        )
        self.assertEqual(response.status_code, 403)


@tag("id_provider")
class FISelectDemarcheTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = AidantFactory()
        self.aidant_yasmina = AidantFactory(
            username="yasmina@yasmina.com",
            organisation=self.aidant_thierry.organisation,
        )
        self.usager = UsagerFactory(given_name="Joséphine")
        self.connection = Connection.objects.create(
            state="avalidstate123", nonce="avalidnonce456", usager=self.usager,
        )
        date_further_away_minus_one_hour = datetime(
            2019, 1, 9, 8, tzinfo=pytz_timezone("Europe/Paris")
        )
        self.connection_2 = Connection.objects.create(
            state="test_expiration_date_triggered",
            nonce="test_nonce",
            usager=self.usager,
            expires_on=date_further_away_minus_one_hour,
        )
        mandat_creation_date = datetime(
            2019, 1, 5, 3, 20, 34, 0, tzinfo=pytz_timezone("Europe/Paris")
        )

        self.mandat_thierry_usager_1 = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=mandat_creation_date + timedelta(days=6),
            creation_date=mandat_creation_date,
        )
        AutorisationFactory(
            mandat=self.mandat_thierry_usager_1, demarche="transports",
        )
        AutorisationFactory(
            mandat=self.mandat_thierry_usager_1, demarche="famille",
        )

        self.mandat_thierry_usager_2 = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=mandat_creation_date + timedelta(days=3),
            creation_date=mandat_creation_date,
        )
        AutorisationFactory(
            mandat=self.mandat_thierry_usager_2, demarche="logement",
        )

    def test_FI_select_demarche_url_triggers_the_fi_select_demarche_view(self):
        self.client.force_login(self.aidant_thierry)
        found = resolve("/select_demarche/")
        self.assertEqual(found.func, id_provider.fi_select_demarche)

    def test_FI_select_demarche_triggers_FI_select_demarche_template(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get(
            "/select_demarche/", data={"connection_id": self.connection.id}
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/id_provider/fi_select_demarche.html"
        )

    date_close = datetime(2019, 1, 6, 9, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(date_close)
    def test_get_demarches_for_one_usager_and_two_autorisations(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get(
            "/select_demarche/", data={"connection_id": self.connection.id}
        )
        demarches = response.context["demarches"]
        autorisations = [demarche for demarche in demarches]
        self.assertIn("famille", autorisations)
        self.assertIn("transports", autorisations)
        self.assertIn("logement", autorisations)
        self.assertEqual(len(autorisations), 3)

    @freeze_time(date_close)
    def test_post_to_select_demarche_triggers_redirect(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/select_demarche/",
            data={"connection_id": self.connection.id, "chosen_demarche": "famille"},
        )
        self.assertEqual(response.status_code, 302)

    @freeze_time(date_close)
    def test_with_another_aidant_from_the_organisation(self):
        self.client.force_login(self.aidant_yasmina)
        response = self.client.post(
            "/select_demarche/",
            data={"connection_id": self.connection.id, "chosen_demarche": "famille"},
        )
        self.assertEqual(response.status_code, 302)

    date_further_away = datetime(2019, 1, 9, 9, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(date_further_away)
    def test_expired_autorisation_does_not_appear(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get(
            "/select_demarche/", data={"connection_id": self.connection.id}
        )
        demarches = response.context["demarches"]
        autorisations = [demarche for demarche in demarches]
        self.assertIn("famille", autorisations)
        self.assertIn("transports", autorisations)
        self.assertNotIn("logement", autorisations)
        self.assertEqual(len(autorisations), 2)

    @freeze_time(date_further_away)
    def test_post_to_select_demarche_with_expired_demarche_triggers_403(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/select_demarche/",
            data={"connection_id": self.connection.id, "chosen_demarche": "logement"},
        )
        self.assertEqual(response.status_code, 403)

    @freeze_time(date_further_away)
    def test_post_to_select_demarche_with_expired_connection_triggers_timeout(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/select_demarche/",
            data={"connection_id": self.connection_2.id, "chosen_demarche": "famille"},
        )
        self.assertEqual(response.status_code, 408)

    @freeze_time(date_further_away)
    def test_post_to_select_demarche_with_unknown_connection_triggers_forbidden(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/select_demarche/",
            data={
                "connection_id": (self.connection_2.id + 1),
                "chosen_demarche": "famille",
            },
        )
        self.assertEqual(response.status_code, 403)


@tag("id_provider")
@override_settings(
    FC_AS_FI_ID="test_client_id",
    FC_AS_FI_SECRET="test_client_secret",
    FC_AS_FI_CALLBACK_URL="test_url.test_url",
    HOST="localhost",
)
@override_settings(FC_CONNECTION_AGE=300)
class TokenTests(TestCase):
    def setUp(self):
        self.code = "test_code"
        self.code_hash = make_password(self.code, settings.FC_AS_FI_HASH_SALT)
        self.usager = UsagerFactory(given_name="Joséphine")
        self.usager.sub = "avalidsub789"
        self.usager.save()
        self.connection = Connection()
        self.connection.state = "avalidstate123"
        self.connection.code = self.code_hash
        self.connection.nonce = "avalidnonce456"
        self.connection.usager = self.usager
        self.connection.expires_on = datetime(
            2012, 1, 14, 3, 21, 34, tzinfo=pytz_timezone("Europe/Paris")
        )
        self.connection.save()
        self.fc_request = {
            "grant_type": "authorization_code",
            "redirect_uri": "test_url.test_url",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "code": self.code,
        }

    def test_token_url_triggers_token_view(self):
        found = resolve("/token/")
        self.assertEqual(found.func, id_provider.token)

    date = datetime(2012, 1, 14, 3, 20, 34, 0, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(date)
    def test_correct_info_triggers_200(self):

        response = self.client.post("/token/", self.fc_request)

        response_content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response_content)
        response_json["access_token"] = make_password(
            response_json["access_token"], settings.FC_AS_FI_HASH_SALT
        )
        connection = Connection.objects.get(code=self.code_hash)
        awaited_response = {
            "access_token": connection.access_token,
            "expires_in": 3600,
            "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJ0ZXN0X2NsaWVu"
            "dF9pZCIsImV4cCI6MTMyNjUxMDk5NCwiaWF0IjoxMzI2NTEwNjk0LCJpc3MiOiJsb2NhbGhvc"
            "3QiLCJzdWIiOiJhdmFsaWRzdWI3ODkiLCJub25jZSI6ImF2YWxpZG5vbmNlNDU2In0.a7nbGA"
            "-Ib9I1HaMb5iC9s4fDP1ZbIXUJpU-YbdYFcWA",
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

    def test_missing_parameters_triggers_bad_request(self):
        for parameter in self.fc_request:
            bad_request = dict(self.fc_request)
            del bad_request[parameter]
            response = self.client.post("/token/", bad_request)
            self.assertEqual(response.status_code, 400)

    date_expired = date + timedelta(seconds=settings.FC_CONNECTION_AGE + 1200)

    @freeze_time(date_expired)
    def test_expired_connection_triggers_timeout(self):
        response = self.client.post("/token/", self.fc_request)
        self.assertEqual(response.status_code, 408)


@tag("id_provider")
class UserInfoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.usager = UsagerFactory(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate=date(1969, 12, 25),
            gender=Usager.GENDER_FEMALE,
            birthplace="70447",
            birthcountry=Usager.BIRTHCOUNTRY_FRANCE,
            sub="test_sub",
            email="User@user.domain",
            creation_date="2019-08-05T15:49:13.972Z",
        )
        self.aidant_thierry = AidantFactory()
        self.mandat_thierry_usager = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        self.autorisation = AutorisationFactory(
            mandat=self.mandat_thierry_usager, demarche="transports",
        )

        self.access_token = "test_access_token"
        self.access_token_hash = make_password(
            self.access_token, settings.FC_AS_FI_HASH_SALT
        )
        self.connection = Connection.objects.create(
            state="avalidstate123",
            code="test_code",
            nonce="avalidnonde456",
            usager=self.usager,
            access_token=self.access_token_hash,
            expires_on=datetime(
                2012, 1, 14, 3, 21, 34, 0, tzinfo=pytz_timezone("Europe/Paris")
            ),
            aidant=self.aidant_thierry,
            autorisation=self.autorisation,
        )

    def test_token_url_triggers_token_view(self):
        found = resolve("/userinfo/")
        self.assertEqual(found.func, id_provider.user_info)

    date = datetime(2012, 1, 14, 3, 20, 34, 0, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(date)
    def test_well_formatted_access_token_returns_200(self):

        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
        )

        FC_formatted_info = {
            "given_name": "Joséphine",
            "family_name": "ST-PIERRE",
            "preferred_username": "ST-PIERRE",
            "birthdate": "1969-12-25",
            "gender": Usager.GENDER_FEMALE,
            "birthplace": "70447",
            "birthcountry": Usager.BIRTHCOUNTRY_FRANCE,
            "sub": self.connection.usager.sub,
            "email": "User@user.domain",
            "creation_date": "2019-08-05T15:49:13.972Z",
        }

        content = response.json()

        self.assertEqual(content, FC_formatted_info)

    @freeze_time(date)
    def test_autorisation_use_triggers_journal_entry(self):

        self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
        )

        journal_entries = Journal.objects.all()

        self.assertEqual(journal_entries.count(), 1)
        self.assertEqual(journal_entries.first().action, "use_autorisation")

    date_expired = date + timedelta(seconds=settings.FC_CONNECTION_AGE + 1200)

    @freeze_time(date_expired)
    def test_expired_connection_returns_timeout(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
        )

        self.assertEqual(response.status_code, 408)

    def test_badly_formatted_authorization_header_triggers_403(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": self.access_token}
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": f"Bearer: {self.access_token}"}
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_token_triggers_403(self):
        response = self.client.get(
            "/userinfo/", **{"HTTP_AUTHORIZATION": "wrong_access_token"}
        )
        self.assertEqual(response.status_code, 403)
