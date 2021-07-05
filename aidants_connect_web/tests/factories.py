from collections import Iterable

import factory
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from aidants_connect_web.models import (
    Autorisation,
    Connection,
    CarteTOTP,
    Mandat,
    Organisation,
    OrganisationType,
    Usager,
    Journal,
)


class OrganisationFactory(factory.DjangoModelFactory):
    name = "COMMUNE D'HOULBEC COCHEREL"
    siret = 123
    address = "45 avenue du Général de Gaulle, 27120 HOULBEC COCHEREL"

    class Meta:
        model = Organisation


class CarteTOTPFactory(factory.DjangoModelFactory):
    seed = "0123456789ABCDEF"
    serial_number = "ABC000001"

    class Meta:
        model = CarteTOTP


class OrganisationTypeFactory(factory.DjangoModelFactory):
    name = "Type par défaut"

    class Meta:
        model = OrganisationType


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

    @factory.post_generation
    def post(self, create, _, **kwargs):
        if not create or not kwargs.get("with_otp_device", False):
            return
        device = self.staticdevice_set.create(id=self.id)
        device.token_set.create(token="123456")


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

    @factory.post_generation
    def post(self, create, _, **kwargs):
        authorisations = kwargs.get("create_authorisations", None)
        if not create or not isinstance(authorisations, Iterable):
            return

        for auth in authorisations:
            Autorisation.objects.create(
                mandat=self,
                demarche=str(auth),
                revocation_date=None,
            )


class ExpiredMandatFactory(MandatFactory):
    expiration_date = factory.LazyAttribute(lambda f: now() - timedelta(days=365))


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


class JournalFactory(factory.DjangoModelFactory):
    class Meta:
        model = Journal

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        creation_date = kwargs.pop("creation_date", None)
        obj = super(JournalFactory, cls)._create(model_class, *args, **kwargs)
        if creation_date is not None:
            Journal.objects.filter(pk=obj.pk).update(creation_date=creation_date)
        return obj


class AttestationJournalFactory(JournalFactory):
    action = "create_attestation"
    is_remote_mandat = False
    access_token = factory.Faker("md5")
    duree = 6
