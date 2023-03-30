from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import reverse

from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_static.models import StaticDevice

from aidants_connect_common.utils.constants import RequestStatusConstants
from aidants_connect_habilitation.admin import OrganisationRequestAdmin
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    OrganisationRequestFactory,
)
from aidants_connect_web.tests.factories import AidantFactory


@tag("admin")
class OrganisationRequestAdminTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org_request_admin = OrganisationRequestAdmin(
            OrganisationRequest, AdminSite()
        )

    @classmethod
    def setUpTestData(cls):
        cls.amac_user = AidantFactory(
            is_staff=True,
        )
        cls.amac_user.set_password("password")
        cls.amac_user.save()
        cls.amac_device = StaticDevice.objects.create(user=cls.amac_user, name="Device")

        cls.amac_client = Client()
        cls.amac_client.force_login(cls.amac_user)
        amac_session = cls.amac_client.session
        amac_session[DEVICE_ID_SESSION_KEY] = cls.amac_device.persistent_id
        amac_session.save()

    def test_send_default_email(self):
        self.assertEqual(len(mail.outbox), 0)

        # this is supposed to one email:
        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.VALIDATED.name,
            data_pass_id=67245456,
        )
        for _ in range(3):
            AidantRequestFactory(organisation=org_request)

        # this is supposed to send another email:
        self.org_request_admin.send_acceptance_email(org_request)

        # so here we expect 2 emails here in outbox:
        self.assertEqual(len(mail.outbox), 2)

        acceptance_message = mail.outbox[1]

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

    def test_acceptance_message_has_waiting_list_message(self):
        self.assertEqual(len(mail.outbox), 0)

        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.VALIDATED.name,
            data_pass_id=67245456,
        )

        self.org_request_admin.send_acceptance_email(org_request)
        self.assertEqual(len(mail.outbox), 2)

        acceptance_message = mail.outbox[1]

        self.assertIn(
            "les formations peuvent être complètes pour les prochaines semaines",
            acceptance_message.body,
        )
        self.assertIn(
            "Vous serez contactés prochainement par l'organisme de formation qui vous "
            "communiquera les dates disponibles pour les formations à venir. ",
            acceptance_message.body,
        )
        self.assertNotIn(
            "Vous pouvez vous inscrire sur liste d’attente ici", acceptance_message.body
        )

    def test_send_email_with_custom_body_and_subject(self):
        self.assertEqual(len(mail.outbox), 0)

        # this is supposed to one email:
        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.VALIDATED.name,
            data_pass_id=67245456,
        )
        for _ in range(3):
            AidantRequestFactory(organisation=org_request)

        # this is supposed to send another email:
        email_body = "Corps du mail iaculis, scelerisque felis non, rutrum purus."
        email_subject = "Objet du mail consequat nisl sed viverra laoreet."
        self.org_request_admin.send_acceptance_email(
            org_request, email_body, email_subject
        )

        # so here we expect 2 emails here in outbox:
        self.assertEqual(len(mail.outbox), 2)
        acceptance_message = mail.outbox[1]

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

    def test_send_refusal_email(self):
        self.assertEqual(len(mail.outbox), 0)

        # this is supposed to one email:
        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.REFUSED.name,
            data_pass_id=67245456,
        )
        for _ in range(3):
            AidantRequestFactory(organisation=org_request)

        # this is supposed to send another email:
        email_body = "Corps du mail iaculis, scelerisque felis non, rutrum purus."
        email_subject = "Objet du mail consequat nisl sed viverra laoreet."
        self.org_request_admin.send_refusal_email(
            org_request, email_body, email_subject
        )

        # so here we expect 2 emails here in outbox:
        self.assertEqual(len(mail.outbox), 2)
        refusal_message = mail.outbox[1]

        # check subject and email contents
        self.assertEqual(email_subject, refusal_message.subject)
        self.assertEqual(email_body, refusal_message.body)

        # check recipients are as expected
        self.assertEqual(
            len(refusal_message.recipients()), 5
        )  # 3 aidants + 1 issuer + 1 manager
        self.assertTrue(
            all(
                aidant.email in refusal_message.recipients()
                for aidant in org_request.aidant_requests.all()
            )
        )
        self.assertTrue(org_request.manager.email in refusal_message.recipients())
        self.assertTrue(org_request.issuer.email in refusal_message.recipients())

    def test_send_changes_required_email(self):
        self.assertEqual(len(mail.outbox), 0)

        # this is supposed to one email:
        org_request = OrganisationRequestFactory(
            status=RequestStatusConstants.REFUSED.name,
            data_pass_id=67245456,
        )
        for _ in range(3):
            AidantRequestFactory(organisation=org_request)

        # this is supposed to send another email:
        content = "Corps du mail iaculis, scelerisque felis non, rutrum purus."
        self.org_request_admin.send_changes_required_message(org_request, content)

        # so here we expect 2 emails here in outbox:
        self.assertEqual(len(mail.outbox), 2)
        changes_required_message = mail.outbox[1]

        # check subject and email contents
        self.assertIn(content, changes_required_message.body)

        # check recipients are as expected
        self.assertEqual(len(changes_required_message.recipients()), 1)
        self.assertTrue(
            org_request.issuer.email in changes_required_message.recipients()
        )

    def test_metier_user_can_see_manager(self):
        org_request = OrganisationRequestFactory()
        url_root = f"admin:{OrganisationRequest._meta.app_label}_{OrganisationRequest.__name__.lower()}"  # noqa
        url = reverse(url_root + "_change", args=(org_request.pk,))
        response = self.amac_client.get(url)
        self.assertContains(response, "<h2>Responsable</h2>")
