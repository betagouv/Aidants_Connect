import tablib
from django.test import tag, TestCase

from aidants_connect_web.admin import OrganisationResource
from aidants_connect_web.models import Organisation
from aidants_connect_web.tests.factories import OrganisationFactory


@tag("admin")
class OrganisationResourceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory(siret="121212122")
        cls.orga_data = tablib.Dataset(
            headers=[
                "Statut de la demande (send = à valider; pending = brouillon)",
                "Code postal de la structure",
                "SIRET de l’organisation",
            ]
        )

    def test_dont_create_new_organisation(self):
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data.append(["validated", "13013", "121212123"])
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())

    def test_dont_raise_exception_without_status(self):
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        invalid_orga_data = tablib.Dataset(
            headers=["Code postal de la structure", "SIRET de l’organisation"]
        )
        invalid_orga_data.append(["13013", "121212122"])
        orga_ressource.import_data(invalid_orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())

    def test_update_organisation_without_zipcode(self):
        self.assertEqual(1, Organisation.objects.all().count())
        orga_ressource = OrganisationResource()
        self.orga_data.append(["validated", "13013", "121212122"])
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("13013", Organisation.objects.first().zipcode)

    def test_dont_update_organisation_with_zipcode(self):
        self.organisation.zipcode = "34034"
        self.organisation.save()
        self.assertEqual(1, Organisation.objects.all().count())

        orga_ressource = OrganisationResource()
        self.orga_data.append(["validated", "13013", "121212122"])
        orga_ressource.import_data(self.orga_data, dry_run=False)
        self.assertEqual(1, Organisation.objects.all().count())
        self.assertEqual("34034", Organisation.objects.first().zipcode)
