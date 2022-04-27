from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase, tag

from aidants_connect.common.constants import RequestStatusConstants
from aidants_connect_habilitation.admin import OrganisationRequestAdmin
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    OrganisationRequestFactory,
)


@tag("admin")
class OrganisationRequestAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_request_admin = OrganisationRequestAdmin(
            OrganisationRequest, AdminSite()
        )

    def test_send_default_email(self):
        self.assertEqual(len(mail.outbox), 0)

        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.VALIDATED.name,
            data_pass_id=67245456,
        )
        for _ in range(3):
            AidantRequestFactory(organisation=org_request)

        # this is supposed to send one email:
        self.org_request_admin.send_acceptance_email(org_request)

        # so here we expect 1 email here in outbox:
        self.assertEqual(len(mail.outbox), 1)
        acceptance_message = mail.outbox[0]

        # check subject and email contents
        self.assertIn(str(org_request.data_pass_id), acceptance_message.subject)
        self.assertTrue(
            all(
                str(aidant) in acceptance_message.body
                for aidant in org_request.aidant_requests.all()
            )
        )
        # check recipients are as expected
        self.assertEqual(
            len(acceptance_message.recipients()), 5
        )  # 3 aidants + 1 issuer + 1 manager
        self.assertTrue(
            all(
                aidant.email in acceptance_message.recipients()
                for aidant in org_request.aidant_requests.all()
            )
        )
        self.assertTrue(org_request.manager.email in acceptance_message.recipients())
        self.assertTrue(org_request.issuer.email in acceptance_message.recipients())

    def test_send_email_with_custom_body_and_subject(self):
        self.assertEqual(len(mail.outbox), 0)

        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.VALIDATED.name,
            data_pass_id=67245456,
        )
        for _ in range(3):
            AidantRequestFactory(organisation=org_request)

        # this is supposed to send one email:
        email_body = "Corps du mail iaculis, scelerisque felis non, rutrum purus."
        email_subject = "Objet du mail consequat nisl sed viverra laoreet."
        self.org_request_admin.send_acceptance_email(
            org_request, email_body, email_subject
        )

        # so here we expect 1 email here in outbox:
        self.assertEqual(len(mail.outbox), 1)
        acceptance_message = mail.outbox[0]

        # check subject and email contents
        self.assertEqual(email_subject, acceptance_message.subject)
        self.assertEqual(email_body, acceptance_message.body)

        # check recipients are as expected
        self.assertEqual(
            len(acceptance_message.recipients()), 5
        )  # 3 aidants + 1 issuer + 1 manager
        self.assertTrue(
            all(
                aidant.email in acceptance_message.recipients()
                for aidant in org_request.aidant_requests.all()
            )
        )
        self.assertTrue(org_request.manager.email in acceptance_message.recipients())
        self.assertTrue(org_request.issuer.email in acceptance_message.recipients())
