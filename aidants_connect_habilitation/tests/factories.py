import factory
from django.conf import settings
from django.core.exceptions import ValidationError
from factory import fuzzy

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
        phone = factory.Faker("phone_number", locale="fr_FR").generate()
        if to_python(phone, settings.PHONENUMBER_DEFAULT_REGION).is_valid():
            break
    else:
        raise ValidationError(
            "Couldn't generate a valid phone number for PhoneNumberField"
        )

    return phone


class IssuerFactory(factory.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    profession = factory.Faker("job")
    phone = factory.LazyFunction(_generate_valid_phone)

    class Meta:
        model = Issuer


class OrganisationRequestFactory(factory.DjangoModelFactory):
    issuer = factory.SubFactory(IssuerFactory)

    draft_id = None

    type_id = fuzzy.FuzzyChoice(
        [x.value for x in RequestOriginConstants if x != RequestOriginConstants.OTHER]
    )
    name = factory.Faker("company")
    siret = fuzzy.FuzzyInteger(111_111_111, 999_999_999)
    address = factory.Faker("street_address")
    zipcode = factory.Faker("postcode")
    city = factory.Faker("city")

    partner_administration = factory.Faker("company")

    public_service_delegation_attestation = ""

    france_services_label = fuzzy.FuzzyChoice([True, False])

    web_site = factory.Faker("url")

    mission_description = fuzzy.FuzzyText(length=12)

    avg_nb_demarches = fuzzy.FuzzyInteger(0)

    manager_first_name = factory.Faker("first_name")
    manager_last_name = factory.Faker("last_name")
    manager_email = factory.Faker("email")
    manager_profession = factory.Faker("job")
    manager_phone = factory.LazyFunction(_generate_valid_phone)

    cgu = True
    dpo = True
    professionals_only = True
    without_elected = True

    class Meta:
        model = OrganisationRequest


class AidantRequestFactory(factory.DjangoModelFactory):
    organisation = factory.SubFactory(OrganisationRequestFactory)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    profession = factory.Faker("job")

    class Meta:
        model = AidantRequest
