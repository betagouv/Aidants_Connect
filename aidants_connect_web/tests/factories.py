from django.contrib.auth import get_user_model
import factory


class UserFactory(factory.DjangoModelFactory):
    username = "thierry@thierry.com"
    email = "thierry@thierry.com"
    password = "motdepassedethierry"
    last_name = "Goneau"
    first_name = "Thierry"
    profession = "secrétaire"
    organisme = "COMMUNE DE HOULBEC COCHEREL"
    ville = "HOULBEC COCHEREL"

    class Meta:
        model = get_user_model()
