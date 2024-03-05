import random
from datetime import timedelta

from django.utils.timezone import now

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
    end_datetime = LazyFunction(lambda: now() + timedelta(days=1))
    type = SubFactory(FormationTypeFactory)
    duration = LazyFunction(lambda: random.randint(1, 10))
    max_attendants = LazyFunction(lambda: random.randint(1, 10))
    status = FuzzyChoice(Formation.Status.values)

    class Meta:
        model = Formation
