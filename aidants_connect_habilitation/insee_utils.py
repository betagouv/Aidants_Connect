from django.conf import settings

from api_insee import ApiInsee
from api_insee.request.request_entreprises import (
    RequestEntrepriseServiceSiren,
    RequestEntrepriseServiceSiret,
)


class ACRequestEntrepriseServiceSiret(RequestEntrepriseServiceSiret):
    path = "/entreprises/sirene/V3.11/siret"


class ACRequestEntrepriseServiceSiren(RequestEntrepriseServiceSiren):
    path = "/entreprises/sirene/V3.11/siren"


def get_client_insee_api():
    api = ApiInsee(key=settings.API_INSEE_KEY, secret=settings.API_INSEE_SECRET)
    api.use("siren", ACRequestEntrepriseServiceSiren)
    api.use("siret", ACRequestEntrepriseServiceSiret)
    return api
