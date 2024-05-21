import json
from datetime import date, datetime, timedelta
from unittest import mock
from unittest.mock import Mock
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db.models.query import QuerySet
from django.template.response import TemplateResponse
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import resolve, reverse
from django.utils import timezone

import jwt
from freezegun import freeze_time

from aidants_connect_web.models import Aidant, Connection, Journal, Usager
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.utilities import generate_id_token
from aidants_connect_web.views import id_provider


@tag("id_provider")
class AuthorizeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.aidant_thierry = AidantFactory()
        cls.aidant_jacques = AidantFactory()
        cls.aidante_sarah = AidantFactory()
        cls.aidante_sarah.organisation.allowed_demarches = ["papiers"]
        cls.aidante_sarah.organisation.save()

        cls.usager = UsagerFactory(given_name="Joséphine", sub="123")

        mandat_1 = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager,
            expiration_date=timezone.now() + timedelta(days=6),
        )

        AutorisationFactory(
            mandat=mandat_1,
            demarche="Revenus",
            revocation_date=timezone.now() - timedelta(days=1),
        )

        mandat_2 = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager,
            expiration_date=timezone.now() + timedelta(days=12),
        )

        AutorisationFactory(
            mandat=mandat_2,
            demarche="Famille",
        )
        AutorisationFactory(
            mandat=mandat_2,
            demarche="Revenus",
        )

        mandat_3 = MandatFactory(
            organisation=cls.aidant_jacques.organisation,
            usager=cls.usager,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=mandat_3,
            demarche="Logement",
        )
        date_further_away_minus_one_hour = datetime(
            2019, 1, 9, 8, tzinfo=ZoneInfo("Europe/Paris")
        )
        cls.connection = Connection.objects.create(
            state="test_expiration_date_triggered",
            nonce="avalidnonce456",
            usager=cls.usager,
            expires_on=date_further_away_minus_one_hour,
        )

        cls.valid_oauth_data = {
            "state": "avalidstate123",
            "nonce": "avalidnonce456",
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL_V2,
            "scope": "openid birth email profile",
            "acr_values": "eidas1",
            "prompt": "login",
        }

    def test_authorize_url_triggers_the_authorize_view(self):
        self.client.force_login(self.aidant_thierry)
        found = resolve("/authorize/")
        self.assertEqual(found.func.view_class, id_provider.Authorize)

    def test_authorize_url_without_arguments_returns_400(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/authorize/")
        self.assertEqual(response.status_code, 400)

    def test_authorize_url_triggers_the_authorize_template(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.get("/authorize/", data=self.valid_oauth_data)

        self.assertTemplateUsed(
            response, "aidants_connect_web/id_provider/authorize.html"
        )

        self.assertEqual(response.status_code, 200)

    def test_authorize_url_without_right_parameters_triggers_bad_request(self):
        self.client.force_login(self.aidant_thierry)

        for data, value in self.valid_oauth_data.items():
            data_with_missing_item = self.valid_oauth_data.copy()
            del data_with_missing_item[data]

            response = self.client.get("/authorize/", data=data_with_missing_item)

            self.assertEqual(
                response.status_code,
                400,
                f"{response.resolver_match.func.view_class} called without parameter "
                f"{data} should return HTTP code 400; got: "
                f"{response.status_code}",
            )

    def test_authorize_url_with_malformed_parameters_triggers_403(self):
        self.client.force_login(self.aidant_thierry)

        dynamic_data = {"state": "avalidstate123", "nonce": "avalidnonce456"}

        for data, value in dynamic_data.items():
            dynamic_data_with_wrong_item = dynamic_data.copy()
            dynamic_data_with_wrong_item[data] = "aninvalidvalue 123"

            sent_data = {**self.valid_oauth_data, **dynamic_data_with_wrong_item}
            response = self.client.get("/authorize/", data=sent_data)

            self.assertEqual(response.status_code, 403)

    def test_authorize_url_with_wrong_parameters_triggers_403(self):
        self.client.force_login(self.aidant_thierry)

        dynamic_data = {"state": "avalidstate123", "nonce": "avalidnonce456"}

        for data, value in self.valid_oauth_data.items():
            static_data_with_wrong_item = self.valid_oauth_data.copy()
            static_data_with_wrong_item[data] = "wrong_data"

            sent_data = {**dynamic_data, **static_data_with_wrong_item}
            response: TemplateResponse = self.client.get("/authorize/", data=sent_data)

            self.assertEqual(
                response.status_code,
                403,
                f"{response.resolver_match.func.view_class} called with parameter "
                f"{data}=wrong_data should return HTTP code 403; got: "
                f"{response.status_code}",
            )

    def test_authorize_sends_the_correct_amount_of_usagers(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.get(
            "/authorize/",
            data=self.valid_oauth_data,
        )

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
                "chosen_usager": connection.usager.id,
                "connection_id": connection.id,
                # Pass valid OAuth data for changing user feature
                **self.valid_oauth_data,
            },
        )

        saved_items = Connection.objects.all().order_by("pk")
        self.assertEqual(saved_items.count(), 2)
        connection = saved_items[1]
        self.assertEqual(connection.usager.sub, "123")
        self.assertNotEqual(connection.nonce, "No Nonce Provided")
        self.assertRedirects(
            response,
            f"{reverse('fi_select_demarche')}?{urlencode(self.valid_oauth_data)}",
            fetch_redirect_response=False,
        )

    @freeze_time(datetime(2019, 1, 9, 9, tzinfo=ZoneInfo("Europe/Paris")))
    def test_post_to_authorize_with_expired_connection_triggers_connection_timeout(
        self,
    ):
        self.client.force_login(self.aidant_thierry)

        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": 1,
                "connection_id": self.connection.pk,
                # Pass valid OAuth data for changing user feature
                **self.valid_oauth_data,
            },
        )
        self.assertEqual(
            response.status_code,
            408,
            f"{response.resolver_match.func.view_class} expired connection should "
            f"return HTTP code 408; got: {response.status_code}",
        )

    def test_post_to_authorize_with_unknown_connection_triggers_forbidden(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": 1,
                "connection_id": self.connection.id + 1,
                # Pass valid OAuth data for changing user feature
                **self.valid_oauth_data,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_post_to_authorize_omitting_connection_triggers_forbidden(self):
        self.client.force_login(self.aidant_thierry)

        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": 1,
                # Pass valid OAuth data for changing user feature
                **self.valid_oauth_data,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_post_to_authorize_with_empty_usager_selection(self):
        self.client.force_login(self.aidant_thierry)
        connection = Connection.objects.create(
            state="avalidstate123", nonce="avalidnonce456", usager=self.usager
        )

        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": "",
                "connection_id": connection.pk,
                # Pass valid OAuth data for changing user feature
                **self.valid_oauth_data,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(
            response.context_data["form"].errors["chosen_usager"],
            [
                "Aucun profil n'a été trouvé.Veuillez taper le nom d'une personne et "
                "la barre de recherche et sélectionner parmis les propositions dans "
                "la liste déroulante"
            ],
        )

    def test_claim_perimeter_restriction(self):
        connection = Connection.objects.create(
            state="avalidstate123", nonce="avalidnonce456", usager=self.usager
        )

        def get_oauth_data(essential=True, values=None):
            return {
                **self.valid_oauth_data,
                "claim": json.dumps(
                    {
                        "id_token": {
                            "rep_scope": {
                                "essential": essential,
                                **({"values": values} if values else {}),
                            }
                        }
                    }
                ),
            }

        # Invalid JSON
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": self.usager.pk,
                "connection_id": connection.pk,
                **self.valid_oauth_data,
                "claim": "test",
            },
        )
        self.assertEqual(403, response.status_code)

        # Invalid perimeters
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": self.usager.pk,
                "connection_id": connection.pk,
                **get_oauth_data(values=["argent", "test"]),
            },
        )
        self.assertEqual(403, response.status_code)

        # essential=false
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": self.usager.pk,
                "connection_id": connection.pk,
                **get_oauth_data(essential=False),
            },
        )
        self.assertEqual(403, response.status_code)

        # Unauthorize parameter
        self.client.force_login(self.aidante_sarah)
        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": self.usager.pk,
                "connection_id": connection.pk,
                **get_oauth_data(values=["famille"]),
            },
        )
        self.assertEqual(403, response.status_code)

        # No perimeter
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": self.usager.pk,
                "connection_id": connection.pk,
                **get_oauth_data(),
            },
        )
        self.assertEqual(302, response.status_code)

        # Valid data
        self.client.force_login(self.aidant_thierry)
        response = self.client.post(
            "/authorize/",
            data={
                "chosen_usager": self.usager.pk,
                "connection_id": connection.pk,
                **get_oauth_data(values=["famille"]),
            },
        )
        self.assertEqual(302, response.status_code)


@tag("id_provider")
class FISelectDemarcheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.code = (
            "r2xKN_qFnQgK0XlwEu_Eii1oa6PrU9yVw1l8yNhh4"
            "vb0ZFUPLaPKb9qL3S8G5VJS7aftiO8jl-0tez72Wi2D6Q"
        )
        cls.aidant_thierry = AidantFactory()
        cls.aidant_yasmina = AidantFactory(
            organisation=cls.aidant_thierry.organisation,
        )
        cls.usager = UsagerFactory(given_name="Joséphine")
        cls.connection = Connection.objects.create(
            state="avalidstate123",
            nonce="avalidnonce456",
            usager=cls.usager,
        )
        date_further_away_minus_one_hour = datetime(
            2019, 1, 9, 8, tzinfo=ZoneInfo("Europe/Paris")
        )
        cls.connection_2 = Connection.objects.create(
            state="test_expiration_date_triggered",
            nonce="test_nonce",
            usager=cls.usager,
            expires_on=date_further_away_minus_one_hour,
        )
        mandat_creation_date = datetime(
            2019, 1, 5, 3, 20, 34, 0, tzinfo=ZoneInfo("Europe/Paris")
        )

        cls.mandat_thierry_usager_1 = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager,
            expiration_date=mandat_creation_date + timedelta(days=6),
            creation_date=mandat_creation_date,
        )
        AutorisationFactory(
            mandat=cls.mandat_thierry_usager_1,
            demarche="transports",
        )
        AutorisationFactory(
            mandat=cls.mandat_thierry_usager_1,
            demarche="famille",
        )

        cls.mandat_thierry_usager_2 = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager,
            expiration_date=mandat_creation_date + timedelta(days=3),
            creation_date=mandat_creation_date,
        )
        AutorisationFactory(
            mandat=cls.mandat_thierry_usager_2,
            demarche="logement",
        )

    def test_FI_select_demarche_url_triggers_the_fi_select_demarche_view(self):
        self.client.force_login(self.aidant_thierry)
        found = resolve("/select_demarche/")
        self.assertEqual(found.func.view_class, id_provider.FISelectDemarche)

    def test_FI_select_demarche_triggers_FI_select_demarche_template(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = self.connection.id
        session.save()
        response = self.client.get("/select_demarche/")
        self.assertTemplateUsed(
            response, "aidants_connect_web/id_provider/fi_select_demarche.html"
        )

    date_close = datetime(2019, 1, 6, 9, tzinfo=ZoneInfo("Europe/Paris"))

    @freeze_time(date_close)
    def test_get_demarches_for_one_usager_and_two_autorisations(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = self.connection.id
        session.save()
        response = self.client.get("/select_demarche/")
        demarches = response.context["demarches"]
        autorisations = [demarche for demarche in demarches]
        self.assertIn("famille", autorisations)
        self.assertIn("transports", autorisations)
        self.assertIn("logement", autorisations)
        self.assertEqual(len(autorisations), 3)

    @freeze_time(date_close)
    @mock.patch("aidants_connect_web.views.id_provider.token_urlsafe")
    def test_post_to_select_demarche_triggers_redirect(self, token_urlsafe_mock: Mock):
        token_urlsafe_mock.return_value = self.code
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = self.connection.id
        session.save()
        response = self.client.post(
            "/select_demarche/",
            data={
                "chosen_demarche": "famille",
                "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"https://fcp.integ01.dev-franceconnect.fr/oidc_callback?"
            f"code={self.code}&state=avalidstate123",
        )

    @freeze_time(date_close)
    @mock.patch("aidants_connect_web.views.id_provider.token_urlsafe")
    def test_with_another_aidant_from_the_organisation(self, token_urlsafe_mock: Mock):
        token_urlsafe_mock.return_value = self.code
        self.client.force_login(self.aidant_yasmina)
        session = self.client.session
        session["connection"] = self.connection.id
        session.save()

        response = self.client.post(
            "/select_demarche/",
            data={
                "chosen_demarche": "famille",
                "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"https://fcp.integ01.dev-franceconnect.fr/oidc_callback?"
            f"code={self.code}&state=avalidstate123",
        )

    date_further_away = datetime(2019, 1, 9, 9, tzinfo=ZoneInfo("Europe/Paris"))

    @freeze_time(date_further_away)
    def test_expired_autorisation_does_not_appear(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = self.connection.id
        session.save()
        response = self.client.get("/select_demarche/")
        demarches = response.context["demarches"]
        autorisations = [demarche for demarche in demarches]
        self.assertIn("famille", autorisations)
        self.assertIn("transports", autorisations)
        self.assertNotIn("logement", autorisations)
        self.assertEqual(len(autorisations), 2)

    @freeze_time(date_further_away)
    def test_post_to_select_demarche_with_expired_demarche_triggers_403(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = self.connection.id
        session.save()
        response = self.client.post(
            "/select_demarche/",
            data={"chosen_demarche": "logement"},
        )
        self.assertEqual(response.status_code, 403)

    @freeze_time(date_further_away)
    def test_post_to_select_demarche_with_expired_connection_triggers_timeout(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = self.connection_2.id
        session.save()
        response = self.client.post(
            "/select_demarche/", data={"chosen_demarche": "famille"}
        )
        self.assertEqual(response.status_code, 408)

    @freeze_time(date_further_away)
    def test_post_to_select_demarche_with_unknown_connection_triggers_forbidden(self):
        self.client.force_login(self.aidant_thierry)
        self.client.session["connection"] = self.connection_2.id + 1
        response = self.client.post(
            "/select_demarche/",
            data={
                "chosen_demarche": "famille",
            },
        )
        self.assertEqual(response.status_code, 403)


@tag("id_provider")
@override_settings(
    FC_AS_FI_ID="test_client_id",
    # we don't need FC_AS_FI_SECRET's value.
    # we use his hash instead.
    HASH_FC_AS_FI_SECRET="e26ade3b37d31920d89e233c447b0d5e51accff2fdc51d1f377b0"
    "31b5d581e70",
    FC_AS_FI_CALLBACK_URL="test_url.test_url",
    FC_AS_FI_CALLBACK_URL_V2="test_url.test_url.v2",
    HOST="localhost",
    FC_AS_FI_HASH_SALT="123456",
)
@override_settings(FC_CONNECTION_AGE=300)
class TokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code = "test_code"
        cls.code_hash = make_password(cls.code, settings.FC_AS_FI_HASH_SALT)
        cls.usager = UsagerFactory(given_name="Joséphine")
        cls.usager.sub = "avalidsub789"
        cls.usager.save()
        cls.connection = Connection()
        cls.connection.state = "avalidstate123"
        cls.connection.code = cls.code_hash
        cls.connection.nonce = "avalidnonce456"
        cls.connection.usager = cls.usager
        cls.connection.expires_on = datetime(
            2012, 1, 14, 3, 21, 34, tzinfo=ZoneInfo("Europe/Paris")
        )
        cls.connection.save()
        cls.fc_request = {
            "grant_type": "authorization_code",
            "redirect_uri": "test_url.test_url",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "code": cls.code,
        }

    def test_token_url_triggers_token_view(self):
        found = resolve("/token/")
        self.assertEqual(found.func.view_class, id_provider.Token)

    date = datetime(2012, 1, 14, 3, 20, 34, 0, tzinfo=ZoneInfo("Europe/Paris"))

    @freeze_time(date)
    @mock.patch(
        "aidants_connect_web.views.id_provider.get_random_string",
        return_value="5ieq7Bg173y99tT6MA",
    )
    def test_correct_info_triggers_200(self, _):
        self.maxDiff = None
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
            "id_token": jwt.encode(
                generate_id_token(connection),
                self.fc_request["client_secret"],
                algorithm="HS256",
            ),
            "refresh_token": "5ieq7bg173y99tt6ma",
            "token_type": "Bearer",
        }

        self.assertEqual(awaited_response, response_json)

        # Test 2nd redirect URL
        request = {**self.fc_request, "redirect_uri": "test_url.test_url.v2"}
        response = self.client.post("/token/", request)
        self.assertEqual(response.status_code, 200)

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
@override_settings(
    # Override salt to get reproductible tests. In particular,
    # on environment where salt is set to an empty string
    FC_AS_FI_HASH_SALT="123456"
)
class UserInfoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.usager = UsagerFactory(
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
            phone="0 800 840 800",
        )
        cls.aidant_thierry = AidantFactory()
        cls.mandat_thierry_usager = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.autorisation = AutorisationFactory(
            mandat=cls.mandat_thierry_usager,
            demarche="transports",
        )

        cls.access_token = "test_access_token"
        cls.access_token_hash = make_password(
            cls.access_token, settings.FC_AS_FI_HASH_SALT
        )
        cls.connection = Connection.objects.create(
            state="avalidstate123",
            code="test_code",
            nonce="avalidnonde456",
            usager=cls.usager,
            access_token=cls.access_token_hash,
            expires_on=datetime(
                2012, 1, 14, 3, 21, 34, 0, tzinfo=ZoneInfo("Europe/Paris")
            ),
            aidant=cls.aidant_thierry,
            organisation=cls.aidant_thierry.organisation,
            autorisation=cls.autorisation,
        )

    def test_token_url_triggers_token_view(self):
        found = resolve("/userinfo/")
        self.assertEqual(found.func, id_provider.user_info)

    date = datetime(2012, 1, 14, 3, 20, 34, 0, tzinfo=ZoneInfo("Europe/Paris"))

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


@tag("id_provider")
class EndSessionEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.usager = UsagerFactory(
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
        cls.aidant_thierry = AidantFactory()
        cls.mandat_thierry_usager = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.autorisation = AutorisationFactory(
            mandat=cls.mandat_thierry_usager,
            demarche="transports",
        )

        cls.access_token = "test_access_token"
        cls.access_token_hash = make_password(
            cls.access_token, settings.FC_AS_FI_HASH_SALT
        )
        cls.connection = Connection.objects.create(
            state="avalidstate123",
            code="test_code",
            nonce="avalidnonde456",
            usager=cls.usager,
            access_token=cls.access_token_hash,
            expires_on=datetime(
                2012, 1, 14, 3, 21, 34, 0, tzinfo=ZoneInfo("Europe/Paris")
            ),
            aidant=cls.aidant_thierry,
            organisation=cls.aidant_thierry.organisation,
            autorisation=cls.autorisation,
        )

    def test_end_session_endpoint_url_triggers_end_session_endpoint_view(self):
        found = resolve("/logout/")
        self.assertEqual(found.func, id_provider.end_session_endpoint)

    def test_nominal_case_redirects_to_FC(self):
        response = self.client.get(
            "/logout/",
            data={
                "post_logout_redirect_uri": settings.FC_AS_FI_LOGOUT_REDIRECT_URI,
                "id_token_hint": self.access_token,
                "state": "avalidstate123",
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_only_accepts_GET_request(self):
        response = self.client.post(
            "/logout/",
            data={
                "post_logout_redirect_uri": settings.FC_AS_FI_LOGOUT_REDIRECT_URI,
                "id_token_hint": self.access_token,
                "state": "avalidstate123",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_only_accepts_preknown_redirect_uri(self):
        response = self.client.get(
            "/logout/",
            data={
                "post_logout_redirect_uri": "bad_uri",
                "id_token_hint": self.access_token,
                "state": "avalidstate123",
            },
        )

        self.assertEqual(response.status_code, 400)
