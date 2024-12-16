from aidants_connect_common.constants import RequestStatusConstants

from .models import OrganisationRequest


def real_fix_orga_request_status(OrganisationRequest):
    orga_requests = OrganisationRequest.objects.filter(status="CHANGES_DONE")
    orga_requests.update(status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name)


def get_orga_req_without_legal_category():
    return OrganisationRequest.objects.filter(legal_category=0)


def get_and_save_insee_informations(organisation, api_insee):
    catlegale = None
    if len(str(organisation.siret)) == 9:
        try:
            res = api_insee.siren(str(organisation.siret)).get()
            catlegale = res["uniteLegale"]["periodesUniteLegale"][0][
                "categorieJuridiqueUniteLegale"
            ]
        except Exception as e:
            print("Erreur SIREN", organisation.siret, e)
    elif len(str(organisation.siret)) == 14:
        try:
            res = api_insee.siret(str(organisation.siret)).get()
            catlegale = res["etablissement"]["uniteLegale"][
                "categorieJuridiqueUniteLegale"
            ]
        except Exception as e:
            print("Erreur SIRET", organisation.siret, e)
    if catlegale:
        organisation.legal_category = catlegale
        organisation.save()
