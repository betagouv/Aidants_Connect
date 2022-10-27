from factory.django import DjangoModelFactory

from aidants_connect_common.models import Department, Region


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department
