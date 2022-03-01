from django.conf import settings
from django.core.exceptions import ValidationError

import factory
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText
from faker import Faker as RealFaker
from phonenumber_field.phonenumber import to_python

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_habilitation.models import (
    AidantRequest,
    DataPrivacyOfficer,
    Issuer,
    Manager,
    OrganisationRequest,
)


def _generate_valid_phone():
    """Sometimes, Faker generates a phone number that PhoneNumberField
    does not consider valid which makes tests to randomly fail. This
    function always generate a valid french phone number for PhoneNumberField"""
    for try_attempt in range(10):
        phone = Faker("phone_number").evaluate(None, None, {"locale": "fr_FR"})
        if to_python(phone, settings.PHONENUMBER_DEFAULT_REGION).is_valid():
            break
    else:
        raise ValidationError(
            "Couldn't generate a valid phone number for PhoneNumberField"
        )

    return phone


class IssuerFactory(DjangoModelFactory):
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    profession = Faker("job")
    phone = LazyFunction(_generate_valid_phone)

    email_verified = True

    class Meta:
        model = Issuer


class DataPrivacyOfficerFactory(DjangoModelFactory):
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    profession = Faker("job")
    phone = LazyFunction(_generate_valid_phone)

    class Meta:
        model = DataPrivacyOfficer


class ManagerFactory(DjangoModelFactory):
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    profession = Faker("job")
    phone = LazyFunction(_generate_valid_phone)

    address = Faker("street_address")
    zipcode = Faker("postcode")
    city = Faker("city")

    is_aidant = FuzzyChoice([True, False])

    class Meta:
        model = Manager


class OrganisationRequestFactory(DjangoModelFactory):
    issuer = SubFactory(IssuerFactory)
    manager = SubFactory(ManagerFactory)
    data_privacy_officer = SubFactory(DataPrivacyOfficerFactory)

    draft_id = None

    type_id = FuzzyChoice(RequestOriginConstants.values)
    name = Faker("company")
    siret = FuzzyInteger(111_111_111, 999_999_999)
    address = Faker("street_address")
    zipcode = Faker("postcode")
    city = Faker("city")

    partner_administration = Faker("company")

    public_service_delegation_attestation = ""

    france_services_label = FuzzyChoice([True, False])

    web_site = Faker("url")

    mission_description = FuzzyText(length=12)

    avg_nb_demarches = FuzzyInteger(0)

    cgu = True
    dpo = True
    professionals_only = True
    without_elected = True

    @factory.lazy_attribute
    def type_other(self):
        return (
            RealFaker().company()
            if self.type_id == RequestOriginConstants.OTHER.value
            else None
        )

    class Meta:
        model = OrganisationRequest


class AidantRequestFactory(DjangoModelFactory):
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    profession = Faker("job")
    organisation = SubFactory(OrganisationRequestFactory)

    class Meta:
        model = AidantRequest
