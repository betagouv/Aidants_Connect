from django.test import tag, TestCase

from aidants_connect.admin import DepartmentFilter
from aidants_connect_web.admin import OrganisationAdmin
from aidants_connect_web.models import Organisation
from aidants_connect_web.tests.factories import OrganisationFactory


@tag("admin")
class DeparmentFilterTests(TestCase):
    def test_generate_filter_list(self):
        result = DepartmentFilter.generate_filter_list()
        self.assertEqual(len(result), 102)
        self.assertEqual(("01", "Ain (01)"), result[0])
        self.assertEqual(("20", "Corse-du-Sud (20)"), result[19])

    def test_lookup(self):
        dep_filter = DepartmentFilter(None, {}, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(None, {})), 102)

    def test_queryset(self):
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="20000")
        OrganisationFactory(zipcode="0")
        corse_filter = DepartmentFilter(
            None, {"department": "20"}, Organisation, OrganisationAdmin
        )
        queryset_corse = corse_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_corse.count())
        self.assertEqual("20000", queryset_corse[0].zipcode)

        bdc_filter = DepartmentFilter(
            None, {"department": "13"}, Organisation, OrganisationAdmin
        )
        queryset_bdc = bdc_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(2, queryset_bdc.count())
        self.assertEqual("13013", queryset_bdc[0].zipcode)

        other_filter = DepartmentFilter(
            None, {"department": "other"}, Organisation, OrganisationAdmin
        )
        queryset_other = other_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_other.count())
        self.assertEqual("0", queryset_other[0].zipcode)
