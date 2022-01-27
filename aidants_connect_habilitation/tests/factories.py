from django.conf import settings
from django.core.exceptions import ValidationError
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText

from phonenumber_field.phonenumber import to_python

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_habilitation.models import (
    AidantRequest,
    OrganisationRequest,
    Issuer,
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

    class Meta:
        model = Issuer


class OrganisationRequestFactory(DjangoModelFactory):
    issuer = SubFactory(IssuerFactory)

    draft_id = None

    type_id = FuzzyChoice(
        [x.value for x in RequestOriginConstants if x != RequestOriginConstants.OTHER]
    )
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

    manager_first_name = Faker("first_name")
    manager_last_name = Faker("last_name")
    manager_email = Faker("email")
    manager_profession = Faker("job")
    manager_phone = LazyFunction(_generate_valid_phone)

    cgu = True
    dpo = True
    professionals_only = True
    without_elected = True

    class Meta:
        model = OrganisationRequest


class AidantRequestFactory(DjangoModelFactory):
    organisation = SubFactory(OrganisationRequestFactory)

    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    profession = Faker("job")

    class Meta:
        model = AidantRequest
