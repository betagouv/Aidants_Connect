from django.conf import settings

from api_insee import ApiInsee
from api_insee.conf import API_VERSION
from api_insee.request.request_entreprises import (
    RequestEntrepriseServiceLiensSuccession,
    RequestEntrepriseServiceSiren,
    RequestEntrepriseServiceSiret,
)
from api_insee.utils.auth_service import AuthService, MockAuth

API_VERSION["path_token"] = "/api-sirene/3.11/token"


class ACAuthService(AuthService):

    def __init__(self, token=False):

        self.token = token


class ACApiInsee(ApiInsee):
    def __init__(self, token, format="json", noauth=False):

        if noauth:
            self.auth = MockAuth()
        else:
            self.auth = ACAuthService(token=token)
        self.format = format

        self.use("siren", RequestEntrepriseServiceSiren)
        self.use("siret", RequestEntrepriseServiceSiret)
        self.use("liens_succession", RequestEntrepriseServiceLiensSuccession)

    def use(self, serviceName, requestService):

        def wrap(*args, **kwargs):
            service = requestService(*args, **kwargs)
            service.format = self.format
            service.useToken(self.auth.token)
            return service

        setattr(self, serviceName, wrap)


class ACRequestEntrepriseServiceSiret(RequestEntrepriseServiceSiret):
    path = "/api-sirene/3.11/siret"

    @property
    def header(self):
        return {
            "Accept": self._accept_format,
            "X-INSEE-Api-Key-Integration": "%s" % (self.token),
        }


class ACRequestEntrepriseServiceSiren(RequestEntrepriseServiceSiren):
    path = "/api-sirene/3.11/siren"

    @property
    def header(self):
        return {
            "Accept": self._accept_format,
            "X-INSEE-Api-Key-Integration": "%s" % (self.token),
        }


def get_client_insee_api():
    api = ACApiInsee(token=settings.API_INSEE_TOKEN)
    api.use("siren", ACRequestEntrepriseServiceSiren)
    api.use("siret", ACRequestEntrepriseServiceSiret)
    return api
