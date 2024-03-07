import random
from datetime import timedelta

from django.utils.timezone import now

import factory
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from ..models import Department, Formation, FormationType, Region


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


class FormationFactory(DjangoModelFactory):
    start_datetime = LazyFunction(now)
    type = SubFactory(FormationTypeFactory)
    duration = LazyFunction(lambda: random.randint(1, 10))
    max_attendants = LazyFunction(lambda: random.randint(1, 10))
    status = FuzzyChoice(Formation.Status.values)

    @factory.lazy_attribute
    def end_datetime(self, *args, **kwargs):
        return self.start_datetime + timedelta(days=1)

    @factory.post_generation
    def type_label(self, create, extracted, **kwargs):
        if create and extracted:
            self.type.label = extracted
            self.type.save()

    class Meta:
        model = Formation
