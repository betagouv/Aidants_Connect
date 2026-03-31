from django.test import TestCase, override_settings
from django.urls import reverse

from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from aidants_connect_web.models import Aidant, Organisation
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

from .admin import add_static_token_for_aidants


@override_settings(ACTIVATE_INFINITY_TOKEN=True)
class AdminAddInfiniteTokenTest(TestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory(username="thierry@example.com")

    def test_add_infinite_token(self):
        self.assertEqual(0, StaticDevice.objects.all().count())
        self.assertEqual(0, StaticToken.objects.all().count())
        for i in range(2):
            add_static_token_for_aidants(None, None, Aidant.objects.all())
            self.assertEqual(1, StaticDevice.objects.all().count())
            self.assertEqual(1, StaticToken.objects.all().count())
            self.assertEqual(
                1, StaticDevice.objects.filter(user=self.aidant_thierry).count()
            )
            self.assertEqual(
                1, StaticToken.objects.filter(device__user=self.aidant_thierry).count()
            )


@override_settings(ACTIVATE_INFINITY_TOKEN=True)
@override_settings(SANDBOX_API_TOKEN="TOKENSANDBOX")
@override_settings(SANDBOX_API_TOKEN="SANDBOX_URL_PADDING")
class AutomaticAddUserTestCase(TestCase):

    def test_automatic_add_user(self):
        data = {
            "first_name": "Test NOM",
            "last_name": "Test PRENOM",
            "profession": "PROFESSION",
            "email": "Test Email",
            "username": "Test Email",
            "organisation__data_pass_id": 424242,
            "organisation__name": "Organisation Test",
            "organisation__siret": "123456789",
            "organisation__address": "Test Address",
            "organisation__city": "Test City",
            "organisation__zipcode": "12345",
            "datapass_id_managers": "",
            "token": "TOKENSANDBOX",
        }
        response = self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(201, response.status_code)

        self.assertEqual(1, Organisation.objects.all().count())
        orga = Organisation.objects.all()[0]
        self.assertEqual(424242, orga.data_pass_id)
        self.assertEqual("Organisation Test", orga.name)

        self.assertEqual(1, Aidant.objects.all().count())
        aidant = Aidant.objects.all()[0]
        self.assertEqual("test email", aidant.username)
        self.assertEqual("test email", aidant.email)
        self.assertEqual(orga, aidant.organisation)

        self.assertEqual(1, StaticDevice.objects.filter(user=aidant).count())
        device = StaticDevice.objects.filter(user=aidant).first()
        self.assertEqual(
            1, StaticToken.objects.filter(device=device, token="123456").count()
        )

    def test_dont_create_twice_organisation_or_aidant(self):
        self.assertEqual(0, Organisation.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        data = {
            "first_name": "Marge",
            "last_name": "Simpson",
            "profession": "aidante",
            "email": "msimpson@simpson.com",
            "username": "msimpson@simpson.com",
            "organisation__data_pass_id": 12121,
            "organisation__name": "L'internationale",
            "organisation__siret": "121212123",
            "organisation__address": "Rue du petit puit",
            "organisation__city": "Marseille",
            "organisation__zipcode": "13001",
            "datapass_id_managers": "",
            "token": "TOKENSANDBOX",
        }
        response = self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(1, Aidant.objects.all().count())
        response = self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(1, Aidant.objects.all().count())
        orga = Organisation.objects.all()[0]
        self.assertEqual(12121, orga.data_pass_id)
        self.assertEqual("L'internationale", orga.name)
        aidant = Aidant.objects.all()[0]
        self.assertEqual("msimpson@simpson.com", aidant.username)
        self.assertEqual("msimpson@simpson.com", aidant.email)

    def test_dont_create_twice_aidant_different_lastname(self):
        self.assertEqual(0, Organisation.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        data = {
            "first_name": "Marge",
            "last_name": "Simpson",
            "profession": "aidante",
            "email": "msimpson@simpson.com",
            "username": "msimpson@simpson.com",
            "organisation__data_pass_id": 12121,
            "organisation__name": "L'internationale",
            "organisation__siret": "121212123",
            "organisation__address": "Rue du petit puit",
            "organisation__city": "Marseille",
            "organisation__zipcode": "13001",
            "datapass_id_managers": "",
            "token": "TOKENSANDBOX",
        }
        response = self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(1, Aidant.objects.all().count())

        data["last_name"] = "Simpson BIS"
        response = self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(1, Aidant.objects.all().count())
        orga = Organisation.objects.all()[0]
        self.assertEqual(12121, orga.data_pass_id)
        self.assertEqual("L'internationale", orga.name)
        aidant = Aidant.objects.all()[0]
        self.assertEqual("msimpson@simpson.com", aidant.username)
        self.assertEqual("msimpson@simpson.com", aidant.email)
        self.assertEqual("Simpson", aidant.last_name)

    def test_import_with_one_managed_orga_is_ok(self):
        self.assertEqual(0, Organisation.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        data = {
            "first_name": "Marge",
            "last_name": "Simpson",
            "profession": "Réferente",
            "email": "msimpson@simpson.com",
            "username": "msimpson@simpson.com",
            "organisation__data_pass_id": 12121,
            "organisation__name": "L'internationale",
            "organisation__siret": "121212123",
            "organisation__address": "Rue du petit puit",
            "organisation__city": "Marseille",
            "organisation__zipcode": "13001",
            "datapass_id_managers": "12121|",
            "token": "TOKENSANDBOX",
        }
        self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(1, Organisation.objects.all().count())
        orga = Organisation.objects.all()[0]
        self.assertEqual(12121, orga.data_pass_id)
        self.assertEqual("L'internationale", orga.name)

        self.assertEqual(1, Aidant.objects.all().count())
        aidant = Aidant.objects.all()[0]
        self.assertEqual("msimpson@simpson.com", aidant.username)
        self.assertEqual("msimpson@simpson.com", aidant.email)
        self.assertEqual(orga, aidant.organisation)
        self.assertEqual(1, aidant.responsable_de.all().count())
        self.assertEqual(orga, aidant.responsable_de.first())

    def test_import_with_two_managed_orga_is_ok(self):
        OrganisationFactory.create(name="Orga2", data_pass_id=22222)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        data = {
            "first_name": "Marge",
            "last_name": "Simpson",
            "profession": "Réferente",
            "email": "msimpson@simpson.com",
            "username": "msimpson@simpson.com",
            "organisation__data_pass_id": 12121,
            "organisation__name": "L'internationale",
            "organisation__siret": "121212123",
            "organisation__address": "Rue du petit puit",
            "organisation__city": "Marseille",
            "organisation__zipcode": "13001",
            "datapass_id_managers": "12121|22222|",
            "token": "TOKENSANDBOX",
        }
        self.client.post(reverse("sandbox_automatic_creation"), data)
        self.assertEqual(2, Organisation.objects.all().count())
        orga = Organisation.objects.filter(data_pass_id=12121)[0]
        self.assertEqual("L'internationale", orga.name)

        self.assertEqual(1, Aidant.objects.all().count())
        aidant = Aidant.objects.all()[0]
        self.assertEqual("msimpson@simpson.com", aidant.username)
        self.assertEqual("msimpson@simpson.com", aidant.email)
        self.assertEqual(orga, aidant.organisation)
        self.assertEqual(2, aidant.responsable_de.all().count())
        self.assertTrue(aidant.responsable_de.filter(data_pass_id=orga.data_pass_id))
        self.assertTrue(aidant.responsable_de.filter(data_pass_id=22222))
