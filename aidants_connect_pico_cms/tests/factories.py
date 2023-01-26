from random import randint

from factory import Faker as FactoryFaker
from factory.django import DjangoModelFactory

from aidants_connect_pico_cms.models import Testimony


class CmsContentFactory(DjangoModelFactory):
    published = True
    slug = FactoryFaker("slug")
    sort_order = randint(1, 50)
    body = FactoryFaker("paragraph")

    class Meta:
        abstract = True


class TestimonyFactory(CmsContentFactory):
    name = FactoryFaker("first_name")
    job = FactoryFaker("job")

    class Meta:
        model = Testimony
