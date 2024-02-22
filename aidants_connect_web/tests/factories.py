import random
from collections.abc import Iterable
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils.timezone import now

from django_otp.plugins.otp_totp.models import TOTPDevice
from factory import (
    Faker,
    LazyAttribute,
    SelfAttribute,
    Sequence,
    SubFactory,
    lazy_attribute,
    post_generation,
)
from factory.django import DjangoModelFactory

from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.models import (
    Autorisation,
    CarteTOTP,
    Connection,
    CoReferentNonAidantRequest,
    HabilitationRequest,
    Journal,
    Mandat,
    Notification,
    Organisation,
    OrganisationType,
    Usager,
)
from aidants_connect_web.utilities import normalize_totp_cart_serial


class OrganisationFactory(DjangoModelFactory):
    name = "COMMUNE D'HOULBEC COCHEREL"
    siret = 123
    address = "45 avenue du Général de Gaulle, 27120 HOULBEC COCHEREL"

    class Meta:
        model = Organisation


class CarteTOTPFactory(DjangoModelFactory):
    seed = Faker("hexify")

    @lazy_attribute
    def serial_number(self):
        for _ in range(10):
            serial = normalize_totp_cart_serial(random.randint(0, 9999))
            if not CarteTOTP.objects.filter(serial_number=serial).exists():
                return serial
        else:
            raise ValueError("Couldn't generate a valid serial number in 10 tries")

    class Meta:
        model = CarteTOTP


class TOTPDeviceFactory(DjangoModelFactory):
    class Meta:
        model = TOTPDevice


class OrganisationTypeFactory(DjangoModelFactory):
    name = "Type par défaut"

    class Meta:
        model = OrganisationType


class AidantFactory(DjangoModelFactory):
    username = Faker("email")
    email = SelfAttribute("username")
    last_name = "Goneau"
    first_name = "Thierry"
    profession = "secrétaire"
    organisation = SubFactory(OrganisationFactory)

    class Meta:
        model = get_user_model()

    @post_generation
    def post(self, create, _, **kwargs):
        if not create:
            return
        with_otp_device = kwargs.get("with_otp_device", False)
        if with_otp_device:
            device = self.staticdevice_set.create(id=self.id)
            if not isinstance(with_otp_device, Iterable) or isinstance(
                with_otp_device, str
            ):
                with_otp_device = [with_otp_device]

            default = 123456
            for item in with_otp_device:
                value = str(item) if str(item).isnumeric() else str(default)
                device.token_set.create(token=value)
                default += 1

        if kwargs.get("is_organisation_manager", False):
            self.responsable_de.add(self.organisation)

        if kwargs.get("with_carte_totp", False):
            confirmed = kwargs.get("with_carte_totp_confirmed", True)
            carte: CarteTOTP = CarteTOTPFactory(aidant=self)
            carte.get_or_create_totp_device(confirmed=confirmed)

    @post_generation
    def password(self, create, value, **_):
        if not create:
            return
        if value:
            self.set_password(value)
        else:
            self.set_password("motdepassedethierry")


class AdminFactory(AidantFactory):
    is_staff = True
    is_active = True


class HabilitationRequestFactory(DjangoModelFactory):
    first_name = "Jean"
    last_name = "Dupont"
    email = Faker("email")
    organisation = SubFactory(OrganisationFactory)
    profession = "Secrétaire"

    class Meta:
        model = HabilitationRequest


class UsagerFactory(DjangoModelFactory):
    given_name = "Homer"
    family_name = "Simpson"
    birthdate = "1902-06-30"
    gender = Usager.GENDER_MALE
    birthplace = "27681"
    birthcountry = Usager.BIRTHCOUNTRY_FRANCE
    email = "homer@simpson.com"
    sub = Sequence(lambda n: f"avalidsub{n}")

    class Meta:
        model = Usager


class MandatFactory(DjangoModelFactory):
    organisation = SubFactory(OrganisationFactory)
    usager = SubFactory(UsagerFactory)
    creation_date = LazyAttribute(lambda f: now())
    duree_keyword = "SHORT"
    expiration_date = LazyAttribute(lambda f: now() + timedelta(days=1))
    is_remote = False

    @lazy_attribute
    def remote_constent_method(self):
        return RemoteConsentMethodChoices.LEGACY.name if self.is_remote else ""

    class Meta:
        model = Mandat

    @post_generation
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


class RevokedMandatFactory(MandatFactory):
    @post_generation
    def post(self, create, _, **kwargs):
        authorisations = kwargs.get("create_authorisations", None)
        if not create or not isinstance(authorisations, Iterable):
            return

        for auth in authorisations:
            Autorisation.objects.create(
                mandat=self,
                demarche=str(auth),
                revocation_date=(now() - timedelta(days=5)),
            )


class RevokedOverYearMandatFactory(MandatFactory):
    @post_generation
    def post(self, create, _, **kwargs):
        authorisations = kwargs.get("create_authorisations", None)
        if not create or not isinstance(authorisations, Iterable):
            return

        for auth in authorisations:
            Autorisation.objects.create(
                mandat=self,
                demarche=str(auth),
                revocation_date=(now() - timedelta(days=365)),
            )


class ExpiredMandatFactory(MandatFactory):
    expiration_date = LazyAttribute(lambda f: now() - timedelta(days=5))


class ExpiredOverYearMandatFactory(MandatFactory):
    expiration_date = LazyAttribute(lambda f: now() - timedelta(days=365))


class AutorisationFactory(DjangoModelFactory):
    demarche = "justice"
    mandat = SubFactory(MandatFactory)
    revocation_date = None

    class Meta:
        model = Autorisation


class LegacyAutorisationFactory(AutorisationFactory):
    # Used to test the migration script that actually *creates* mandats ^^
    mandat = None

    class Meta:
        model = Autorisation


class ConnectionFactory(DjangoModelFactory):
    mandat_is_remote = False

    @lazy_attribute
    def remote_constent_method(self):
        return RemoteConsentMethodChoices.LEGACY.name if self.mandat_is_remote else ""

    class Meta:
        model = Connection


class JournalFactory(DjangoModelFactory):
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
    access_token = Faker("md5")
    duree = 6


class NotificationFactory(DjangoModelFactory):
    aidant = SubFactory(AidantFactory)

    class Meta:
        model = Notification


class CoReferentNonAidantRequestFactory(DjangoModelFactory):
    email = Faker("email")
    organisation = SubFactory(OrganisationFactory)

    class Meta:
        model = CoReferentNonAidantRequest
