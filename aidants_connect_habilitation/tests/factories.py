from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError

from factory import Faker as FactoryFaker
from factory import LazyFunction, SubFactory
from factory import lazy_attribute as factory_lazy_attribute
from factory import post_generation
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyInteger, FuzzyText
from faker import Faker
from phonenumber_field.phonenumber import to_python

from aidants_connect_common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_common.utils.gouv_address_api import Address, AddressType
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    Manager,
    OrganisationRequest,
)


def _generate_valid_phone():
    """Sometimes, FactoryFaker generates a phone number that PhoneNumberField
    does not consider valid which makes tests to randomly fail. This
    function always generate a valid french phone number for PhoneNumberField"""
    for try_attempt in range(10):
        phone = Faker("fr_FR").phone_number()
        if to_python(phone, settings.PHONENUMBER_DEFAULT_REGION).is_valid():
            break
    else:
        raise ValidationError(
            "Couldn't generate a valid phone number for PhoneNumberField"
        )

    return phone


class IssuerFactory(DjangoModelFactory):
    first_name = FactoryFaker("first_name")
    last_name = FactoryFaker("last_name")
    email = FactoryFaker("email")
    profession = FactoryFaker("job")
    phone = LazyFunction(_generate_valid_phone)

    email_verified = True

    class Meta:
        model = Issuer


class ManagerFactory(DjangoModelFactory):
    first_name = FactoryFaker("first_name")
    last_name = FactoryFaker("last_name")
    email = FactoryFaker("email")
    profession = FactoryFaker("job")
    phone = LazyFunction(_generate_valid_phone)
    city_insee_code = ""
    department_insee_code = ""
    address = FactoryFaker("street_address")
    zipcode = FactoryFaker("postcode")
    city = FactoryFaker("city")
    conseiller_numerique = False

    is_aidant = True

    class Meta:
        model = Manager


class OrganisationRequestFactory(DjangoModelFactory):
    issuer = SubFactory(IssuerFactory)
    manager = SubFactory(ManagerFactory)

    uuid = LazyFunction(uuid4)
    data_pass_id = FuzzyInteger(10_000_000, 99_999_999)

    status = RequestStatusConstants.AC_VALIDATION_PROCESSING.name

    type_id = RequestOriginConstants.SECRETARIATS_MAIRIE.value
    name = FactoryFaker("company")
    siret = FuzzyInteger(111_111_111, 999_999_999)
    address = FactoryFaker("street_address")
    zipcode = FactoryFaker("postcode")
    city = FactoryFaker("city")

    france_services_label = False

    web_site = FactoryFaker("url")

    mission_description = FuzzyText(length=12)

    avg_nb_demarches = FuzzyInteger(0)

    cgu = True
    not_free = True
    dpo = True
    professionals_only = True
    without_elected = True

    @factory_lazy_attribute
    def type_other(self):
        return (
            Faker().company()
            if self.type_id == RequestOriginConstants.OTHER.value
            else ""
        )

    @post_generation
    def post(self, create, _, **kwargs):
        if not create:
            return

        aidants_count = kwargs.get("aidants_count", None)
        if aidants_count:
            for i in range(aidants_count):
                AidantRequestFactory(organisation=self)

    class Meta:
        model = OrganisationRequest


class DraftOrganisationRequestFactory(OrganisationRequestFactory):
    manager = None

    status = RequestStatusConstants.NEW.name
    data_pass_id = None


class AidantRequestFactory(DjangoModelFactory):
    first_name = FactoryFaker("first_name")
    last_name = FactoryFaker("last_name")
    email = FactoryFaker("email")
    profession = FactoryFaker("job")
    organisation = SubFactory(OrganisationRequestFactory)
    conseiller_numerique = False

    class Meta:
        model = AidantRequest


def address_factory(
    id: str = None,
    name: str = None,
    label: str = None,
    score: float = None,
    postcode: str = None,
    city: str = None,
    citycode: str = "",
    department_number: str = None,
    department_name: str = None,
    region: str = None,
    type: AddressType = None,
) -> Address:
    fake = Faker("fr_FR")
    _street = fake.street_address()
    _zipcode = fake.postcode()
    _city = fake.city()
    _label = f"{_street} {_zipcode} {_city}"

    context = {
        "department_number": department_number or fake.department_number(),
        "department_name": department_name or fake.department_name(),
        "region": region or fake.region(),
    }

    return Address(
        id=(id or fake.text(max_nb_chars=200)),
        name=(name or _street),
        label=(label or _label),
        score=(score or fake.random.randint(0, 100) / 100),
        postcode=(postcode or _zipcode),
        city=(city or _city),
        citycode=citycode,
        context=context,
        type=(type or fake.random.choice(AddressType.values())),
    )
