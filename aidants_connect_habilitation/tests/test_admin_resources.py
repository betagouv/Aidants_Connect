from django.contrib.admin.sites import AdminSite
from django.test import TestCase, tag
from django.test.client import RequestFactory

from aidants_connect_habilitation.admin import OrganisationRequestAdmin
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory


@tag("admin")
class OrganisationRequestResourceTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()
        cls.orga_request_1 = OrganisationRequestFactory(name="MAIRIE 1")
        cls.orga_request_2 = OrganisationRequestFactory(name="MAIRIE 2")

    def test_export_organisation_request(self):
        request = self.rf.get("/", {})
        orga_requests = OrganisationRequest.objects.all()
        orga_request_admin = OrganisationRequestAdmin(OrganisationRequest, AdminSite())
        data = orga_request_admin.get_data_for_export(request, orga_requests)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0][3], "MAIRIE 1")
        self.assertEqual(data[1][3], "MAIRIE 2")
