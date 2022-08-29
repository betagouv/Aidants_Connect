from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase, tag
from django.test.client import RequestFactory

from aidants_connect.admin import DepartmentFilter, RegionFilter
from aidants_connect_common.models import Region
from aidants_connect_web.admin import HabilitationRequestAdmin, OrganisationAdmin
from aidants_connect_web.models import HabilitationRequest, Organisation
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


@tag("admin")
class DepartmentFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()

    def test_generate_filter_list(self):
        result = DepartmentFilter.generate_filter_list()
        self.assertEqual(len(result), 102)
        self.assertEqual(("01", "Ain (01)"), result[0])
        self.assertEqual(("2A", "Corse-du-Sud (20)"), result[19])

    def test_lookup(self):
        request = self.rf.get("/")
        dep_filter = DepartmentFilter(request, {}, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(request, {})), 102)

    def test_lookups_with_selected_region(self):
        params = {
            "region": Region.objects.get(name="Provence-Alpes-Côte d'Azur").insee_code
        }
        request = self.rf.get("/", params)
        dep_filter = DepartmentFilter(request, params, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(request, {})), 6)

    def test_queryset(self):
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="20000")
        OrganisationFactory(zipcode="0")
        corse_filter = DepartmentFilter(
            self.rf.get("/"), {"department": "20"}, Organisation, OrganisationAdmin
        )
        queryset_corse = corse_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_corse.count())
        self.assertEqual("20000", queryset_corse[0].zipcode)

        bdc_filter = DepartmentFilter(
            self.rf.get("/"), {"department": "13"}, Organisation, OrganisationAdmin
        )
        queryset_bdc = bdc_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(2, queryset_bdc.count())
        self.assertEqual("13013", queryset_bdc[0].zipcode)

        other_filter = DepartmentFilter(
            self.rf.get("/"), {"department": "other"}, Organisation, OrganisationAdmin
        )
        queryset_other = other_filter.queryset(
            self.rf.get("/"), Organisation.objects.all()
        )
        self.assertEqual(1, queryset_other.count())
        self.assertEqual("0", queryset_other[0].zipcode)


@tag("admin")
class RegionFilterTests(TestCase):
    def test_queryset(self):
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="20000")
        OrganisationFactory(zipcode="0")
        corse_filter = RegionFilter(
            None,
            {"region": Region.objects.get(name="Corse").insee_code},
            Organisation,
            OrganisationAdmin,
        )
        queryset_corse = corse_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_corse.count())
        self.assertEqual("20000", queryset_corse[0].zipcode)

        paca_filter = RegionFilter(
            None,
            {
                "region": Region.objects.get(
                    name="Provence-Alpes-Côte d'Azur"
                ).insee_code
            },
            Organisation,
            OrganisationAdmin,
        )
        queryset_paca = paca_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(2, queryset_paca.count())
        self.assertEqual("13013", queryset_paca[0].zipcode)

        other_filter = RegionFilter(
            None, {"region": "other"}, Organisation, OrganisationAdmin
        )
        queryset_other = other_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_other.count())
        self.assertEqual("0", queryset_other[0].zipcode)


@tag("admin")
class HabilitationRequestAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory()
        cls.habilitation_request = HabilitationRequestFactory(
            organisation=cls.organisation
        )
        cls.habilitation_request_admin = HabilitationRequestAdmin(
            HabilitationRequest, AdminSite()
        )
        cls.manager = AidantFactory(
            organisation=cls.organisation, post__is_organisation_manager=True
        )

    def test_send_validation_email(self):
        self.assertEqual(len(mail.outbox), 0)

        self.habilitation_request_admin.send_validation_email(self.habilitation_request)

        self.assertEqual(len(mail.outbox), 1)

        validation_message = mail.outbox[0]

        self.assertIn(
            str(self.habilitation_request.first_name), validation_message.subject
        )

        self.assertEqual(len(validation_message.recipients()), 1)
        self.assertTrue(
            all(
                manager.email in validation_message.recipients()
                for manager in self.habilitation_request.organisation.responsables.all()
            )
        )

    def test_send_refusal_email(self):
        self.assertEqual(len(mail.outbox), 0)

        self.habilitation_request_admin.send_refusal_email(self.habilitation_request)

        self.assertEqual(len(mail.outbox), 1)

        refusal_message = mail.outbox[0]

        self.assertIn(
            str(self.habilitation_request.first_name), refusal_message.subject
        )

        self.assertEqual(len(refusal_message.recipients()), 1)
        self.assertTrue(
            all(
                manager.email in refusal_message.recipients()
                for manager in self.habilitation_request.organisation.responsables.all()
            )
        )
