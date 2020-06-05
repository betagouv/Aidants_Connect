import factory
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from aidants_connect_web.models import (
    Autorisation,
    Connection,
    Mandat,
    Organisation,
    Usager,
)


class OrganisationFactory(factory.DjangoModelFactory):
    name = "COMMUNE D'HOULBEC COCHEREL"
    siret = 123
    address = "45 avenue du Général de Gaulle, 27120 HOULBEC COCHEREL"

    class Meta:
        model = Organisation


class AidantFactory(factory.DjangoModelFactory):
    username = "thierry@thierry.com"
    email = "thierry@thierry.com"
    password = "motdepassedethierry"
    last_name = "Goneau"
    first_name = "Thierry"
    profession = "secrétaire"
    organisation = factory.SubFactory(OrganisationFactory)

    class Meta:
        model = get_user_model()


class UsagerFactory(factory.DjangoModelFactory):
    given_name = "Homer"
    family_name = "Simpson"
    birthdate = "1902-06-30"
    gender = Usager.GENDER_MALE
    birthplace = "27681"
    birthcountry = Usager.BIRTHCOUNTRY_FRANCE
    email = "homer@simpson.com"
    sub = factory.Sequence(lambda n: f"avalidsub{n}")

    class Meta:
        model = Usager


class ConnectionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Connection


class MandatFactory(factory.DjangoModelFactory):
    organisation = factory.SubFactory(OrganisationFactory)
    usager = factory.SubFactory(UsagerFactory)
    creation_date = factory.LazyAttribute(lambda f: now())
    duree_keyword = "SHORT"
    expiration_date = factory.LazyAttribute(lambda f: now() + timedelta(days=1))

    class Meta:
        model = Mandat


# Bad data to replace redundant data in autorisation


class RandoOrganisationFactory(factory.DjangoModelFactory):
    name = "Rando Org"
    siret = 123
    address = "45 avenue du Général de Gaulle, 27120 HOULBEC COCHEREL"

    class Meta:
        model = Organisation


class RandoAidantFactory(factory.DjangoModelFactory):
    username = "rando@rando.com"
    email = "rando@rando.com"
    password = "motdepassederando"
    last_name = "Rando"
    first_name = "Rando"
    profession = "Rando"
    organisation = factory.SubFactory(RandoOrganisationFactory)

    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)


class RandoUsagerFactory(factory.DjangoModelFactory):
    given_name = "Rando"
    family_name = "Rando"
    birthdate = "1952-06-30"
    gender = Usager.GENDER_FEMALE
    birthplace = "29681"
    birthcountry = Usager.BIRTHCOUNTRY_FRANCE
    email = "Rando"
    sub = factory.Sequence(lambda n: f"avalidsub{n}")

    class Meta:
        model = Usager
        django_get_or_create = ("sub",)


class AutorisationFactory(factory.DjangoModelFactory):
    demarche = "justice"
    mandat = factory.SubFactory(MandatFactory)
    revocation_date = None
    # redundant data
    aidant = factory.SubFactory(RandoAidantFactory)
    usager = factory.SubFactory(RandoUsagerFactory)
    expiration_date = factory.LazyAttribute(lambda f: now() - timedelta(days=1))

    class Meta:
        model = Autorisation
