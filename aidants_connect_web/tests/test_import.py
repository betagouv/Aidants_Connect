from django.test import TestCase, tag

from aidants_connect_web.models import HabilitationRequest
from aidants_connect_web.tests.factories import (
    HabilitationRequestFactory,
    OrganisationFactory,
)

from ..constants import HabilitationRequestStatuses
from ..management.commands.import_last_eric_files import import_one_row


@tag("import_files")
class ImportEricLastFileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga1 = OrganisationFactory(data_pass_id=3234)
        cls.orga2 = OrganisationFactory(data_pass_id=5555)

        cls.hab_req = HabilitationRequestFactory(
            first_name="Bowser", organisation=cls.orga2
        )

    def test_create_habilitation_request(self):
        self.assertEqual(1, HabilitationRequest.objects.all().count())
        import_one_row([3234, "Marge", "Simpson", "m.simpson@test.com"])
        self.assertEqual(2, HabilitationRequest.objects.all().count())

        self.assertTrue(
            HabilitationRequest.objects.filter(
                last_name="Simpson",
                first_name="Marge",
                email="m.simpson@test.com",
                organisation__data_pass_id=3234,
            )
        )

    def test_change_status_habilitation_request_already_exists(self):
        HabilitationRequestFactory(
            last_name="Simpson",
            first_name="Marge",
            email="m.simpson@test.com",
            organisation=self.orga1,
            status=HabilitationRequestStatuses.STATUS_NEW.value,
        )
        self.assertEqual(2, HabilitationRequest.objects.all().count())
        import_one_row([3234, "Marge", "Simpson", "m.simpson@test.com"])
        self.assertEqual(2, HabilitationRequest.objects.all().count())

        self.assertTrue(
            HabilitationRequest.objects.filter(
                last_name="Simpson",
                first_name="Marge",
                email="m.simpson@test.com",
                organisation__data_pass_id=3234,
                status=HabilitationRequestStatuses.STATUS_PROCESSING.value,
            )
        )

    def test_change_status_habilitation_request_already_exists_waiting_list(self):
        HabilitationRequestFactory(
            last_name="Simpson",
            first_name="Marge",
            email="m.simpson@test.com",
            organisation=self.orga1,
            status=HabilitationRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        )
        self.assertEqual(2, HabilitationRequest.objects.all().count())
        import_one_row([3234, "Marge", "Simpson", "m.simpson@test.com"])
        self.assertEqual(2, HabilitationRequest.objects.all().count())

        self.assertTrue(
            HabilitationRequest.objects.filter(
                last_name="Simpson",
                first_name="Marge",
                email="m.simpson@test.com",
                organisation__data_pass_id=3234,
                status=HabilitationRequestStatuses.STATUS_PROCESSING.value,
            )
        )

    def test_dont_habilitation_request_with_invalid_orga(self):
        self.assertEqual(1, HabilitationRequest.objects.all().count())
        import_one_row([113234, "Marge", "Simpson", "m.simpson@test.com"])
        self.assertEqual(1, HabilitationRequest.objects.all().count())
