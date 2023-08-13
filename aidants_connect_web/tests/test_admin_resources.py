from datetime import datetime

from django.contrib.admin.sites import AdminSite
from django.test import TestCase, tag
from django.test.client import RequestFactory

import pytz
import tablib

from aidants_connect_web.admin import (
    HabilitationRequestAdmin,
    HabilitationRequestImportDateFormationResource,
    OrganisationAdmin,
    OrganisationResource,
)
from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


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


@tag("admin")
class HabilitationRequestResourceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga = OrganisationFactory(data_pass_id=75010029)
        cls.orga2 = OrganisationFactory(data_pass_id=75010030)
        cls.aidant_a_former = HabilitationRequestFactory(
            email="pix@email.com",
            test_pix_passed=True,
            date_test_pix=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=cls.orga,
        )
        cls.aidant_a_former_no_test_pix = HabilitationRequestFactory(
            email="nopix@email.com",
            organisation=cls.orga,
        )
        cls.data = tablib.Dataset(
            headers=[
                "email",
                "data_pass_id",
                "date_formation",
            ]
        )
        cls.aidant_a_former_1 = HabilitationRequestFactory(
            email="two.orgas@email.com",
            test_pix_passed=True,
            date_test_pix=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=cls.orga,
        )
        cls.aidant_a_former_2 = HabilitationRequestFactory(
            email="two.orgas@email.com",
            test_pix_passed=True,
            date_test_pix=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=cls.orga2,
        )

    def test_update_date_formation_and_create_aidant(self):
        self.assertEqual(4, HabilitationRequest.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        habilitation_request_ressource = (
            HabilitationRequestImportDateFormationResource()
        )
        self.data._data = list()
        self.data.append(
            ["pix@email.com", 75010029, datetime(2022, 1, 1, tzinfo=pytz.UTC)]
        )

        habilitation_request_ressource.import_data(self.data, dry_run=False)

        aidant_a_former = HabilitationRequest.objects.filter(
            email=self.aidant_a_former.email
        )[0]
        self.assertTrue(aidant_a_former.formation_done)
        self.assertEqual(
            aidant_a_former.date_formation, datetime(2022, 1, 1, tzinfo=pytz.UTC)
        )
        self.assertEqual(1, Aidant.objects.all().count())

    def test_update_date_formation_and_dont_create_aidant(self):
        self.assertEqual(4, HabilitationRequest.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        habilitation_request_ressource = (
            HabilitationRequestImportDateFormationResource()
        )
        self.data._data = list()
        self.data.append(
            ["nopix@email.com", 75010029, datetime(2022, 1, 1, tzinfo=pytz.UTC)]
        )

        habilitation_request_ressource.import_data(self.data, dry_run=False)

        aidant_a_former = HabilitationRequest.objects.filter(
            email=self.aidant_a_former_no_test_pix.email
        )[0]
        self.assertTrue(aidant_a_former.formation_done)
        self.assertEqual(
            aidant_a_former.date_formation, datetime(2022, 1, 1, tzinfo=pytz.UTC)
        )
        self.assertEqual(0, Aidant.objects.all().count())

    def test_update_date_formation_and_create_aidant_has_two_orgas(self):
        self.assertEqual(4, HabilitationRequest.objects.all().count())
        self.assertEqual(0, Aidant.objects.all().count())
        habilitation_request_ressource = (
            HabilitationRequestImportDateFormationResource()
        )
        self.data._data = list()
        self.data.append(
            ["two.orgas@email.com", 75010029, datetime(2022, 1, 1, tzinfo=pytz.UTC)]
        )

        habilitation_request_ressource.import_data(self.data, dry_run=False)

        aidant_a_former_1 = HabilitationRequest.objects.filter(
            email=self.aidant_a_former_1.email
        )[0]
        self.assertTrue(aidant_a_former_1.formation_done)
        self.assertEqual(
            aidant_a_former_1.date_formation, datetime(2022, 1, 1, tzinfo=pytz.UTC)
        )
        self.assertEqual(aidant_a_former_1.status, HabilitationRequest.STATUS_VALIDATED)

        aidant_a_former_2 = HabilitationRequest.objects.filter(
            email=self.aidant_a_former_1.email
        )[1]
        self.assertTrue(aidant_a_former_2.formation_done)
        self.assertEqual(
            aidant_a_former_2.date_formation, datetime(2022, 1, 1, tzinfo=pytz.UTC)
        )
        self.assertEqual(aidant_a_former_2.status, HabilitationRequest.STATUS_VALIDATED)

        self.assertEqual(
            1, Aidant.objects.filter(email=aidant_a_former_1.email).count()
        )
        aidant = Aidant.objects.filter(email=aidant_a_former_1.email)[0]
        self.assertIn(self.orga, aidant.organisations.all())
        self.assertIn(self.orga2, aidant.organisations.all())


@tag("admin")
class OrganisationResourceExportForSandboxTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()
        cls.organisation1 = OrganisationFactory(
            name="MAIRIE", siret="121212121", data_pass_id=1
        )
        cls.organisation2 = OrganisationFactory(
            name="MAIRIE2", siret="121212122", data_pass_id=2
        )
        cls.organisation3 = OrganisationFactory(
            name="MAIRIE3", siret="121212123", data_pass_id=3
        )

        cls.aidant_marge = AidantFactory(
            first_name="Marge", organisation=cls.organisation1
        )
        cls.aidant_marge.responsable_de.add(cls.organisation1)
        cls.aidant_homer = AidantFactory(
            first_name="Homer", organisation=cls.organisation2
        )
        cls.habilit_bowser = HabilitationRequestFactory(
            first_name="Bowser", organisation=cls.organisation3
        )
        cls.aidant_marge.responsable_de.add(cls.organisation1)

    def get_list_for_export_sandbox(self):
        orgas = Organisation.objects.filter(
            pk__in=[self.organisation1.pk, self.organisation3.pk]
        )

        export_list = OrganisationAdmin.get_list_for_export_sandbox(orgas)
        self.assertEqual(len(export_list), 2)
        self.assertTrue(self.aidant_marge in export_list)
        self.assertTrue(self.habilit_bowser in export_list)

    def test_export_for_sandbox(self):
        request = self.rf.get("/", {})
        orgas = Organisation.objects.filter(
            pk__in=[self.organisation1.pk, self.organisation3.pk]
        )
        orga_admin = OrganisationAdmin(Organisation, AdminSite())
        data = orga_admin.get_data_for_export(request, orgas)
        self.assertEqual(len(data), 2)
        self.assertEqual(len(data[0]), 13)
        self.assertEqual(data[0][1], "Marge")
        self.assertEqual(data[0][3], self.aidant_marge.email)
        self.assertEqual(data[1][1], "Bowser")

    def test_export_for_sandbox_responsable_de(self):
        request = self.rf.get("/", {})
        orgas = Organisation.objects.filter(
            pk__in=[self.organisation1.pk, self.organisation3.pk]
        )
        orga_admin = OrganisationAdmin(Organisation, AdminSite())
        data = orga_admin.get_data_for_export(request, orgas)
        self.assertEqual(data[0][12], f"{self.organisation1.data_pass_id}|")
        self.assertEqual(data[1][12], "")

        self.aidant_marge.responsable_de.add(self.organisation2)
        data = orga_admin.get_data_for_export(request, orgas)
        self.assertEqual(
            data[0][12],
            f"{self.organisation1.data_pass_id}|{self.organisation2.data_pass_id}|",
        )
        self.assertEqual(data[1][12], "")


@tag("admin")
class HabilitationRequestsResourceExportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()
        cls.organisation1 = OrganisationFactory(
            name="MAIRIE", siret="121212121", city="Marseille"
        )
        cls.organisation2 = OrganisationFactory(
            name="MAIRIE2", siret="121212122", zipcode="13013"
        )

        cls.habilit_homer = HabilitationRequestFactory(
            first_name="Homer", organisation=cls.organisation1
        )
        cls.habilit_bowser = HabilitationRequestFactory(
            first_name="Bowser", organisation=cls.organisation2
        )

    def test_export(self):
        request = self.rf.get("/", {})
        hrequests = HabilitationRequest.objects.filter(
            pk__in=[self.habilit_homer.pk, self.habilit_bowser.pk]
        )
        hrequest_admin = HabilitationRequestAdmin(Organisation, AdminSite())
        data = hrequest_admin.get_data_for_export(request, hrequests)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0][10], "Homer")
        self.assertEqual(data[0][15], "Marseille")
        self.assertEqual(data[0][16], "")
        self.assertEqual(data[0][17], "")
        self.assertEqual(data[1][10], "Bowser")
        self.assertEqual(data[1][16], "Bouches-du-Rhône")
        self.assertEqual(data[1][17], "Provence-Alpes-Côte d'Azur")
