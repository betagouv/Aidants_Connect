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


class MandatFactory(factory.DjangoModelFactory):
    organisation = factory.SubFactory(OrganisationFactory)
    usager = factory.SubFactory(UsagerFactory)
    creation_date = factory.LazyAttribute(lambda f: now())
    duree_keyword = "SHORT"
    expiration_date = factory.LazyAttribute(lambda f: now() + timedelta(days=1))

    class Meta:
        model = Mandat


class AutorisationFactory(factory.DjangoModelFactory):
    demarche = "justice"
    mandat = factory.SubFactory(MandatFactory)
    revocation_date = None

    class Meta:
        model = Autorisation


class LegacyAutorisationFactory(AutorisationFactory):

    # Used to test the migration script that actually *creates* mandats ^^
    mandat = None

    class Meta:
        model = Autorisation


class ConnectionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Connection
