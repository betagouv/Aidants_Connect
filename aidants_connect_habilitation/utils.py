from django.conf import settings

from pynsee.sirene import get_sirene_data
from pynsee.utils import init_conn

from aidants_connect_common.constants import RequestStatusConstants

from .models import OrganisationRequest


def real_fix_orga_request_status(OrganisationRequest):
    orga_requests = OrganisationRequest.objects.filter(status="CHANGES_DONE")
    orga_requests.update(status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name)


def get_orga_req_without_legal_category():
    return OrganisationRequest.objects.filter(legal_category=0)


def get_and_save_insee_informations(organisation):
    init_conn(sirene_key=settings.NEW_API_INSEE_TOKEN)
    try:
        res = list(get_sirene_data(str(organisation.siret)).itertuples())[0]
        catlegale = res.categorieJuridiqueUniteLegale
        organisation.legal_category = catlegale
        organisation.save()
    except Exception as e:
        print("Erreur SIREN", organisation.siret, e)
