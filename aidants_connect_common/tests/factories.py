import random
from datetime import timedelta
from typing import Collection

from django.utils.timezone import now

import factory
import faker
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from ..models import Department, Formation, FormationOrganization, FormationType, Region


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department


class FormationTypeFactory(DjangoModelFactory):
    label = Faker("word")

    class Meta:
        model = FormationType


class FormationOrganizationFactory(DjangoModelFactory):
    name = Faker("word")

    @factory.lazy_attribute
    def contacts(self, *args, **kwargs):
        fake = faker.Faker()
        return [fake.email() for _ in range(10)]

    class Meta:
        model = FormationOrganization


class FormationFactory(DjangoModelFactory):
    start_datetime = LazyFunction(now)
    type = SubFactory(FormationTypeFactory)
    duration = LazyFunction(lambda: random.randint(1, 10))
    max_attendants = LazyFunction(lambda: random.randint(10, 100))
    status = FuzzyChoice(Formation.Status.values)
    organisation = SubFactory(FormationOrganizationFactory)

    @factory.lazy_attribute
    def end_datetime(self, *args, **kwargs):
        return self.start_datetime + timedelta(days=1)

    @factory.post_generation
    def type_label(self, create, extracted, **kwargs):
        if create and extracted:
            self.type.label = extracted
            self.type.save()

    @factory.post_generation
    def attendants(self, create, extracted, **kwargs):
        if create and isinstance(extracted, Collection):
            for attendant in extracted:
                if self.max_attendants < len(extracted):
                    self.max_attendants = len(extracted)
                    self.save()
                self.register_attendant(attendant)

    class Meta:
        model = Formation
