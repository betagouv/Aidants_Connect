from django.test import TestCase, override_settings, tag

import tablib
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from aidants_connect_web.models import Aidant, Organisation
from aidants_connect_web.tests.factories import AidantFactory

from .admin import AidantSandboxResource, add_static_token_for_aidants


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


@tag("admin")
class OrganisationResourceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.import_data = tablib.Dataset(
            headers=[
                "id",
                "first_name",
                "last_name",
                "email",
                "organisation__data_pass_id",
                "organisation__name",
                "organisation__siret",
                "organisation__address",
                "organisation__city",
                "organisation__zipcode",
                "organisation__type__id",
                "organisation__type__name",
            ]
        )

    def test_simple_creation_is_ok(self):
        self.assertEqual(0, Organisation.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        self.import_data._data = list()

        import_ressource = AidantSandboxResource()
        self.import_data.append(
            [
                1,
                "Marge",
                "Simpson",
                "msimpson@simpson.com",
                12121,
                "L'internationale",
                "121212123",
                "Rue du petit puit",
                "Marseille",
                13001,
                "",
                "",
            ]
        )

        import_ressource.import_data(self.import_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        orga = Organisation.objects.all()[0]
        self.assertEqual(12121, orga.data_pass_id)
        self.assertEqual("L'internationale", orga.name)

        self.assertEqual(1, Aidant.objects.all().count())
        aidant = Aidant.objects.all()[0]
        self.assertEqual("msimpson@simpson.com", aidant.username)
        self.assertEqual("msimpson@simpson.com", aidant.email)
        self.assertEqual(orga, aidant.organisation)

    def test_dont_create_twice_organisation_or_aidant(self):
        self.assertEqual(0, Organisation.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        self.import_data._data = list()

        import_ressource = AidantSandboxResource()
        self.import_data.append(
            [
                1,
                "Marge",
                "Simpson",
                "msimpson@simpson.com",
                12121,
                "L'internationale",
                "121212123",
                "Rue du petit puit",
                "Marseille",
                13001,
                "",
                "",
            ]
        )

        import_ressource.import_data(self.import_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(1, Aidant.objects.all().count())

        import_ressource.import_data(self.import_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(1, Aidant.objects.all().count())

        orga = Organisation.objects.all()[0]
        self.assertEqual(12121, orga.data_pass_id)
        self.assertEqual("L'internationale", orga.name)
        aidant = Aidant.objects.all()[0]
        self.assertEqual("msimpson@simpson.com", aidant.username)
        self.assertEqual("msimpson@simpson.com", aidant.email)
