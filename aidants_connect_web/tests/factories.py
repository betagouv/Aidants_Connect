from django.contrib.auth import get_user_model
from aidants_connect_web.models import Organisation
import factory


class OrganisationFactory(factory.DjangoModelFactory):
    name = "COMMUNE D'HOULBEC COCHEREL"
    siret = 123
    address = "45 avenue du Général de Gaulle, 27120 HOULBEC COCHEREL"

    class Meta:
        model = Organisation


class UserFactory(factory.DjangoModelFactory):
    username = "thierry@thierry.com"
    email = "thierry@thierry.com"
    password = "motdepassedethierry"
    last_name = "Goneau"
    first_name = "Thierry"
    profession = "secrétaire"
    organisation = factory.SubFactory(OrganisationFactory)

    class Meta:
        model = get_user_model()
