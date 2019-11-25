from django.contrib.auth import get_user_model
from aidants_connect_web.models import Organisation
import factory


class OrganisationFactory(factory.DjangoModelFactory):
    name = "COMMUNE DE HOULBEC COCHEREL"
    siret = 123
    address = "45 avenue du Général de Gaulle, 90210 Beverly Hills"

    class Meta:
        model = Organisation


class UserFactory(factory.DjangoModelFactory):
    username = "thierry@thierry.com"
    email = "thierry@thierry.com"
    password = "motdepassedethierry"
    last_name = "Goneau"
    first_name = "Thierry"
    profession = "secrétaire"
    organisme = "COMMUNE DE HOULBEC COCHEREL"
    ville = "HOULBEC COCHEREL"
    organisation = factory.SubFactory(OrganisationFactory)

    class Meta:
        model = get_user_model()
