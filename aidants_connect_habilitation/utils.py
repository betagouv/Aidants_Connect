from aidants_connect.common.constants import RequestStatusConstants


def real_fix_orga_request_status(OrganisationRequest):
    orga_requests = OrganisationRequest.objects.filter(
        status="Modifications finalisées"
    )
    orga_requests.update(status=RequestStatusConstants.AC_VALIDATION_PROCESSING)
