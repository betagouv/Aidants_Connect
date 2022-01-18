from django.test import tag, TestCase
from django.test.client import RequestFactory

from aidants_connect.admin import DepartmentFilter, RegionFilter
from aidants_connect_web.admin import OrganisationAdmin
from aidants_connect_web.models import Organisation
from aidants_connect_web.tests.factories import OrganisationFactory


@tag("admin")
class DepartmentFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()

    def test_generate_filter_list(self):
        result = DepartmentFilter.generate_filter_list()
        self.assertEqual(len(result), 102)
        self.assertEqual(("01", "Ain (01)"), result[0])
        self.assertEqual(("20", "Corse-du-Sud (20)"), result[19])

    def test_lookup(self):
        request = self.rf.get("/")
        dep_filter = DepartmentFilter(request, {}, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(request, {})), 102)

    def test_lookups_with_selected_region(self):
        params = {"region": "6"}
        request = self.rf.get("/", params)
        dep_filter = DepartmentFilter(request, params, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(request, {})), 10)

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
            None, {"region": "5"}, Organisation, OrganisationAdmin
        )
        queryset_corse = corse_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_corse.count())
        self.assertEqual("20000", queryset_corse[0].zipcode)

        paca_filter = RegionFilter(
            None, {"region": "17"}, Organisation, OrganisationAdmin
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
