import tablib
from django.test import tag, TestCase

from aidants_connect_web.admin import OrganisationResource
from aidants_connect_web.models import Organisation
from aidants_connect_web.tests.factories import OrganisationFactory


@tag("admin")
class OrganisationResourceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory(name="MAIRIE", siret="121212122")
        cls.orga_data = tablib.Dataset(
            headers=[
                "Numéro de demande",
                "Nom de la structure",
                "Statut de la demande (send = à valider; pending = brouillon)",
                "Code postal de la structure",
                "SIRET de l’organisation",
                "Ville de la structure",
            ]
        )

    def test_dont_create_new_organisation(self):
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "L'internationale", "validated", "13013", "121212123", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())

    def test_dont_raise_exception_without_status(self):
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        invalid_orga_data = tablib.Dataset(
            headers=[
                "Numéro de demande",
                "Nom de la structure",
                "Code postal de la structure",
                "SIRET de l’organisation",
            ]
        )
        invalid_orga_data.append(["2323", "L'internationale", "13013", "121212122"])
        orga_ressource.import_data(invalid_orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())

    def test_update_organisation_without_zipcode_city_and_datapassid(self):
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("13013", Organisation.objects.first().zipcode)
        self.assertEqual(2323, Organisation.objects.first().data_pass_id)
        self.assertEqual("Marseille", Organisation.objects.first().city)

    def test_dont_update_organisation_with_zipcode(self):
        self.organisation.refresh_from_db()
        self.organisation.zipcode = "34034"
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())

        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("34034", Organisation.objects.first().zipcode)
        self.assertEqual("Marseille", Organisation.objects.first().city)

    def test_dont_raise_exception_(self):
        self.organisation.refresh_from_db()
        self.organisation.zipcode = "34034"
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())

        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("34034", Organisation.objects.first().zipcode)

    def test_dont_raise_exception_multiple_same_siret(self):
        OrganisationFactory(name="MAIRIE12", siret="121212122")

        self.assertEqual(2, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(2, Organisation.objects.all().count())

    def test_update_organisation_with_zipcode_and_without_datapassid(self):
        self.organisation.refresh_from_db()
        self.organisation.zipcode = "34034"
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("34034", Organisation.objects.first().zipcode)
        self.assertEqual(2323, Organisation.objects.first().data_pass_id)

    def test_update_organisation_without_city(self):
        self.organisation.refresh_from_db()
        self.organisation.data_pass_id = 2323
        self.organisation.zipcode = "34034"
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["1234", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("34034", Organisation.objects.first().zipcode)
        self.assertEqual(2323, Organisation.objects.first().data_pass_id)
        self.assertEqual("Marseille", Organisation.objects.first().city)

    def test_update_organisation_zipcode_when_orga_has_already_datapassid(self):
        self.organisation.refresh_from_db()
        self.organisation.data_pass_id = 2323
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("0", Organisation.objects.first().zipcode)
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["2323", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(2323, Organisation.objects.first().data_pass_id)
        self.assertEqual("13013", Organisation.objects.first().zipcode)

    def test_dont_update_organisation_with_same_name_and_siret_but_another_datapass_id(
        self,
    ):
        self.organisation.refresh_from_db()
        self.organisation.data_pass_id = 2323
        self.organisation.zipcode = "34034"
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data._data = list()
        self.orga_data.append(
            ["4444", "MAIRIE", "validated", "13013", "121212122", "Marseille"]
        )
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual(2323, Organisation.objects.first().data_pass_id)
        self.assertEqual("34034", Organisation.objects.first().zipcode)
