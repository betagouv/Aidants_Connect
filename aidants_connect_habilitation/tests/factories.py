from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError

from factory import Faker as FactoryFaker
from factory import LazyFunction, SubFactory
from factory import lazy_attribute as factory_lazy_attribute
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText
from faker import Faker
from phonenumber_field.phonenumber import to_python

from aidants_connect.common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    DataPrivacyOfficer,
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


class DataPrivacyOfficerFactory(DjangoModelFactory):
    first_name = FactoryFaker("first_name")
    last_name = FactoryFaker("last_name")
    email = FactoryFaker("email")
    profession = FactoryFaker("job")
    phone = LazyFunction(_generate_valid_phone)

    class Meta:
        model = DataPrivacyOfficer


class ManagerFactory(DjangoModelFactory):
    first_name = FactoryFaker("first_name")
    last_name = FactoryFaker("last_name")
    email = FactoryFaker("email")
    profession = FactoryFaker("job")
    phone = LazyFunction(_generate_valid_phone)

    address = FactoryFaker("street_address")
    zipcode = FactoryFaker("postcode")
    city = FactoryFaker("city")

    is_aidant = FuzzyChoice([True, False])

    class Meta:
        model = Manager


class OrganisationRequestFactory(DjangoModelFactory):
    issuer = SubFactory(IssuerFactory)
    manager = SubFactory(ManagerFactory)
    data_privacy_officer = SubFactory(DataPrivacyOfficerFactory)

    uuid = LazyFunction(uuid4)

    status = FuzzyChoice(
        [
            value
            for value in RequestStatusConstants.values()
            if value != RequestStatusConstants.NEW.name
        ]
    )

    type_id = FuzzyChoice(RequestOriginConstants.values)
    name = FactoryFaker("company")
    siret = FuzzyInteger(111_111_111, 999_999_999)
    address = FactoryFaker("street_address")
    zipcode = FactoryFaker("postcode")
    city = FactoryFaker("city")

    partner_administration = FactoryFaker("company")

    public_service_delegation_attestation = ""

    france_services_label = FuzzyChoice([True, False])

    web_site = FactoryFaker("url")

    mission_description = FuzzyText(length=12)

    avg_nb_demarches = FuzzyInteger(0)

    cgu = True
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

    class Meta:
        model = OrganisationRequest


class DraftOrganisationRequestFactory(OrganisationRequestFactory):
    manager = None
    data_privacy_officer = None

    status = RequestStatusConstants.NEW.name


class AidantRequestFactory(DjangoModelFactory):
    first_name = FactoryFaker("first_name")
    last_name = FactoryFaker("last_name")
    email = FactoryFaker("email")
    profession = FactoryFaker("job")
    organisation = SubFactory(OrganisationRequestFactory)

    class Meta:
        model = AidantRequest
