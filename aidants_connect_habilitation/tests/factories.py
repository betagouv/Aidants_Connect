import factory
from factory import fuzzy

from aidants_connect.constants import RequestOriginConstants
from aidants_connect_habilitation.models import OrganisationRequest, Issuer


class IssuerFactory(factory.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    profession = factory.Faker("job")
    phone = factory.Faker("phone_number")

    class Meta:
        model = Issuer


class OrganisationRequestFactory(factory.DjangoModelFactory):
    issuer = factory.SubFactory(IssuerFactory)
    type_id = fuzzy.FuzzyChoice(
        [x.value for x in RequestOriginConstants if x != RequestOriginConstants.OTHER]
    )
    name = factory.Faker("company")
    address = factory.Faker("street_address")
    zipcode = factory.Faker("postcode")
    city = factory.Faker("city")

    partner_administration = factory.Faker("company")

    public_service_delegation_attestation = None

    france_services_label = fuzzy.FuzzyChoice([True, False])

    web_site = factory.Faker("url")

    avg_nb_demarches = fuzzy.FuzzyInteger(0)

    manager_first_name = factory.Faker("first_name")
    manager_last_name = factory.Faker("last_name")
    manager_email = factory.Faker("email")
    manager_profession = factory.Faker("job")
    manager_phone = factory.Faker("phone_number")

    cgu = True
    dpo = True
    professionals_only = True
    without_elected = True

    class Meta:
        model = OrganisationRequest
