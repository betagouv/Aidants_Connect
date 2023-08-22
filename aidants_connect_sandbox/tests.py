from django.test import TestCase, override_settings, tag

import tablib
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from aidants_connect_web.models import Aidant, Organisation
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

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
                "Data pass Id Orga Responsable",
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

    def test_import_with_one_managed_orga_is_ok(self):
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
                "12121|",
            ]
        )
        self.assertEqual(1, len(self.import_data._data))

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
        self.assertEqual(1, aidant.responsable_de.all().count())
        self.assertEqual(orga, aidant.responsable_de.first())

    def test_import_with_two_managed_orga_is_ok(self):
        OrganisationFactory.create(name="Orga2", data_pass_id=22222)
        self.assertEqual(1, Organisation.objects.all().count())
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
                "12121|22222|",
            ]
        )
        self.assertEqual(1, len(self.import_data._data))

        import_ressource.import_data(self.import_data, dry_run=False)
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
