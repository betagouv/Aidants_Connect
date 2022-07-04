from django.test import TestCase, tag

from aidants_connect.common.constants import RequestStatusConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory
from aidants_connect_habilitation.utils import real_fix_orga_request_status


@tag("models")
class OrganisationRequestMigrationTests(TestCase):
    def test_real_fix_orga_request_status(self):
        OrganisationRequestFactory(
            status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        )
        OrganisationRequestFactory(status="CHANGES_DONE")
        OrganisationRequestFactory(status=RequestStatusConstants.NEW.name)
        OrganisationRequestFactory(status=RequestStatusConstants.CHANGES_REQUIRED.name)

        self.assertEqual(
            1,
            OrganisationRequest.objects.filter(
                status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
            ).count(),
        )  # noqa

        self.assertEqual(
            1,
            OrganisationRequest.objects.filter(
                status=RequestStatusConstants.NEW.name
            ).count(),
        )

        self.assertEqual(
            1,
            OrganisationRequest.objects.filter(
                status=RequestStatusConstants.CHANGES_REQUIRED.name
            ).count(),
        )

        self.assertEqual(
            1,
            OrganisationRequest.objects.filter(status="CHANGES_DONE").count(),
        )

        real_fix_orga_request_status(OrganisationRequest)

        self.assertEqual(
            2,
            OrganisationRequest.objects.filter(
                status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name
            ).count(),
        )  # noqa

        self.assertEqual(
            1,
            OrganisationRequest.objects.filter(
                status=RequestStatusConstants.NEW.name
            ).count(),
        )

        self.assertEqual(
            1,
            OrganisationRequest.objects.filter(
                status=RequestStatusConstants.CHANGES_REQUIRED.name
            ).count(),
        )

        self.assertEqual(
            0,
            OrganisationRequest.objects.filter(status="CHANGES_DONE").count(),
        )
