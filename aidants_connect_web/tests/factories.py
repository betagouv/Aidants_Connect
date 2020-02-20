import factory

from django.contrib.auth import get_user_model

from aidants_connect_web.models import Mandat, Organisation, Usager


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
    gender = "male"
    birthplace = 27681
    birthcountry = 99100
    email = "homer@simpson.com"
    sub = "123"

    class Meta:
        model = Usager


class MandatFactory(factory.DjangoModelFactory):
    aidant = factory.SubFactory(AidantFactory)
    usager = factory.SubFactory(UsagerFactory)
    demarche = "justice"

    class Meta:
        model = Mandat
