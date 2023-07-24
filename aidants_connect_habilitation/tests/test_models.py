from datetime import timedelta
from unittest.mock import ANY, Mock, patch

from django.core import mail
from django.db import IntegrityError
from django.forms import model_to_dict
from django.http import HttpRequest
from django.test import TestCase, override_settings, tag
from django.utils.timezone import now

from django_otp.plugins.otp_totp.models import TOTPDevice
from freezegun import freeze_time

from aidants_connect_common.utils.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    IssuerEmailConfirmation,
    Manager,
    OrganisationRequest,
)
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    IssuerFactory,
    ManagerFactory,
    OrganisationRequestFactory,
)
from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    OrganisationFactory,
)


@tag("models")
class OrganisationRequestTests(TestCase):
    def test_type_other_correctly_set_constraint(self):
        OrganisationRequestFactory(
            type_id=RequestOriginConstants.CCAS.value, type_other=""
        )

        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(
                type_id=RequestOriginConstants.OTHER.value, type_other=""
            )
        self.assertIn("type_other_correctly_set", str(cm.exception))

    def test_cgu_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(cgu=False)
        self.assertIn("cgu_checked", str(cm.exception))

    def test_dpo_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(dpo=False)
        self.assertIn("dpo_checked", str(cm.exception))

    def test_professionals_only_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(professionals_only=False)
        self.assertIn("professionals_only_checked", str(cm.exception))

    def test_without_elected_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(without_elected=False)
        self.assertIn("without_elected_checked", str(cm.exception))

    def test_manager_set_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(manager=None)
        self.assertIn("manager_set", str(cm.exception))

    def test_accept_when_it_should_work_fine(self):
        def prepare_data_for_nominal_case():
            organisation_request = OrganisationRequestFactory()
            for _ in range(3):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        def prepare_data_for_org_with_type_other():
            organisation_request = OrganisationRequestFactory(
                type_id=RequestOriginConstants.OTHER.value,
                type_other="My other type value",
            )
            for _ in range(3):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        def prepare_data_with_existing_responsable():
            organisation_request = OrganisationRequestFactory()
            # existing manager
            AidantFactory(
                email=organisation_request.manager.email,
                username=organisation_request.manager.email,
                can_create_mandats=False,
            )
            for _ in range(3):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        for organisation_request in (
            prepare_data_for_nominal_case(),
            prepare_data_for_org_with_type_other(),
            prepare_data_with_existing_responsable(),
        ):
            result = organisation_request.accept_request_and_create_organisation()

            # verify if organisation was created
            self.assertTrue(result, "Result of method call should be True")
            self.assertTrue(
                Organisation.objects.filter(
                    data_pass_id=organisation_request.data_pass_id
                ).exists(),
                "Organisation should have been created",
            )
            organisation = Organisation.objects.get(
                data_pass_id=organisation_request.data_pass_id
            )

            # verify if organisation was added to organisation_request
            self.assertEqual(organisation_request.organisation, organisation)

            # verify if référent aidant account was properly created and added to org
            self.assertEqual(
                1,
                Aidant.objects.filter(email=organisation_request.manager.email).count(),
            )
            responsable = Aidant.objects.get(email=organisation_request.manager.email)

            # verify if référent was added to organisation
            self.assertIn(responsable, organisation.responsables.all())
            self.assertFalse(responsable.can_create_mandats)

            # verify status
            self.assertEqual(
                organisation_request.status, RequestStatusConstants.VALIDATED.name
            )

            # verify if aidants were created
            for aidant_request in organisation_request.aidant_requests.all():
                self.assertTrue(
                    HabilitationRequest.objects.filter(
                        organisation=organisation, email=aidant_request.email
                    ).exists(),
                    f"Habilitation request was not created for {aidant_request.email}",
                )
            # check if référent is on the list of aidants too
            self.assertTrue(
                HabilitationRequest.objects.filter(
                    organisation=organisation,
                    email=organisation_request.manager.email,
                    origin=HabilitationRequest.ORIGIN_HABILITATION,
                ).exists()
            )

    def test_accept_with_a_non_aidant_responsable(self):
        def prepare_data_with_new_responsable():
            organisation_request = OrganisationRequestFactory(
                manager=ManagerFactory(is_aidant=False)
            )
            for _ in range(2):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        organisation_request = prepare_data_with_new_responsable()
        organisation_request.accept_request_and_create_organisation()
        created_organisation = Organisation.objects.get(
            data_pass_id=organisation_request.data_pass_id
        )
        created_manager = Aidant.objects.get(
            username=organisation_request.manager.email
        )
        self.assertFalse(created_manager.can_create_mandats)
        self.assertIn(created_manager, created_organisation.responsables.all())
        self.assertFalse(
            HabilitationRequest.objects.filter(
                email=created_manager.email, organisation=created_organisation
            ).exists()
        )

        def prepare_data_with_existing_aidant_responsable():
            organisation_request = OrganisationRequestFactory(
                manager=ManagerFactory(is_aidant=False, email="dave@lopeur.net")
            )
            AidantFactory(username="dave@lopeur.net", can_create_mandats=True)
            for _ in range(2):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        organisation_request = prepare_data_with_existing_aidant_responsable()
        organisation_request.accept_request_and_create_organisation()
        created_organisation = Organisation.objects.get(
            data_pass_id=organisation_request.data_pass_id
        )
        created_manager = Aidant.objects.get(
            username=organisation_request.manager.email
        )
        self.assertTrue(created_manager.can_create_mandats)
        self.assertIn(created_manager, created_organisation.responsables.all())
        self.assertFalse(
            HabilitationRequest.objects.filter(
                email=created_manager.email, organisation=created_organisation
            ).exists()
        )

    def accept_when_responsable_already_has_totp_card_closes_request(self):
        manager = AidantFactory(username="manager@email.com")
        carte = CarteTOTPFactory(
            serial_number="A456", seed="FA169F10A9", aidant=manager
        )
        device = TOTPDevice(
            tolerance=30, key=carte.seed, user=manager, step=60, confirmed=True
        )
        device.save()
        organisation = OrganisationFactory()
        manager.responsable_de.add(organisation)
        organisation_request = OrganisationRequestFactory(
            manager=ManagerFactory(is_aidant=False, email="manager@email.com"),
            organisation=organisation,
        )
        for _ in range(2):
            AidantRequestFactory(organisation=organisation_request)
        organisation_request.save()
        organisation_request.accept_request_and_create_organisation()

        valid_organisation_requests = OrganisationRequest.objects.filter(
            organisation__in=manager.responsable_de.all()
        )

        self.assertEqual(
            valid_organisation_requests[0].status, RequestStatusConstants.CLOSED.name
        )

    def test_accept_fails_when_organisation_already_exists(self):
        def prepare_data():
            OrganisationFactory(
                data_pass_id=67245456,
            )
            organisation_request = OrganisationRequestFactory(
                status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
                data_pass_id=67245456,
            )
            organisation_request.manager.is_aidant = True
            organisation_request.manager.save()
            for _ in range(3):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        organisation_request = prepare_data()
        with self.assertRaises(Organisation.AlreadyExists):
            organisation_request.accept_request_and_create_organisation(),

        # verify status
        self.assertEqual(
            organisation_request.status,
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
        )

    def test_modifications_request(self):
        self.assertEqual(len(mail.outbox), 0)

        def prepare_data():
            OrganisationFactory(
                data_pass_id=67245456,
            )
            organisation_request = OrganisationRequestFactory(
                status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
                data_pass_id=67245456,
            )
            organisation_request.manager.is_aidant = True
            organisation_request.manager.save()
            for _ in range(3):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        organisation_request = prepare_data()
        # expect one email when creating one organisation request
        self.assertEqual(len(mail.outbox), 1)

        organisation_request.require_changes_request()

        self.assertEqual(
            organisation_request.status,
            RequestStatusConstants.CHANGES_REQUIRED.name,
        )

    def test_refuse_request(self):
        self.assertEqual(len(mail.outbox), 0)

        def prepare_data():
            OrganisationFactory(
                data_pass_id=67245456,
            )
            organisation_request = OrganisationRequestFactory(
                status=RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
                data_pass_id=67245456,
            )
            organisation_request.manager.is_aidant = True
            organisation_request.manager.save()
            for _ in range(3):
                AidantRequestFactory(organisation=organisation_request)
            organisation_request.save()
            return organisation_request

        organisation_request = prepare_data()
        # expect one email when creating one organisation request
        self.assertEqual(len(mail.outbox), 1)

        organisation_request.refuse_request()

        self.assertEqual(
            organisation_request.status,
            RequestStatusConstants.REFUSED.name,
        )

    def test_go_in_waiting_again(self):
        organisation_request = OrganisationRequestFactory(
            status=RequestStatusConstants.REFUSED.name
        )
        organisation_request.go_in_waiting_again()

        self.assertEqual(
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
            organisation_request.status,
        )


class TestIssuerEmailConfirmation(TestCase):
    NOW = now()
    EXPIRE_DAYS = 6
    EMAIL_FROM = "test@test.test"
    EMAIL_SUBJECT = "Subject"

    @override_settings(EMAIL_CONFIRMATION_EXPIRE_DAYS=EXPIRE_DAYS)
    @freeze_time(NOW)
    def test_key_expired(self):
        issuer: Issuer = IssuerFactory(email_verified=False)
        send_limit = self.NOW - timedelta(days=self.EXPIRE_DAYS)

        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=issuer, sent=send_limit + timedelta(seconds=1)
        )

        self.assertFalse(email_confirmation.key_expired)

        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=issuer, sent=send_limit - timedelta(seconds=1)
        )

        self.assertTrue(email_confirmation.key_expired)

    @patch(
        "aidants_connect_habilitation.models.get_random_string",
        return_value="ph1odxqrd3kd5tveroyxjnctlhveevtkusqvd96lar5fb1zhvdzbgwuenkwdtmqs",
    )
    @freeze_time(NOW)
    def test_for_issuer(self, _):
        issuer: Issuer = IssuerFactory(email_verified=False)
        email_confirmation = IssuerEmailConfirmation.for_issuer(issuer)

        self.assertEqual(
            email_confirmation.key,
            "ph1odxqrd3kd5tveroyxjnctlhveevtkusqvd96lar5fb1zhvdzbgwuenkwdtmqs",
        )
        self.assertEqual(email_confirmation.issuer, issuer)
        self.assertEqual(email_confirmation.created, self.NOW)

    @override_settings(EMAIL_CONFIRMATION_EXPIRE_DAYS=EXPIRE_DAYS)
    def test_confirm_saves_issuer_model(self):
        issuer: Issuer = IssuerFactory(email_verified=False)
        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=issuer, sent=now() + timedelta(days=365)
        )

        with patch("aidants_connect_habilitation.models.Issuer.save") as mock_save:
            self.assertFalse(issuer.email_verified)
            self.assertEqual(email_confirmation.confirm(), issuer.email)
            self.assertTrue(issuer.email_verified)
            # Ensure mocking correctly works for the next test
            mock_save.assert_called()

    @override_settings(EMAIL_CONFIRMATION_EXPIRE_DAYS=EXPIRE_DAYS)
    def test_confirm_on_already_confirmed_user_just_return_email(self):
        issuer: Issuer = IssuerFactory(email_verified=True)
        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=issuer, sent=now() - timedelta(days=self.EXPIRE_DAYS + 3)
        )

        with patch("aidants_connect_habilitation.models.Issuer.save") as mock_save:
            self.assertTrue(issuer.email_verified)
            self.assertEqual(email_confirmation.confirm(), issuer.email)
            self.assertTrue(issuer.email_verified)
            mock_save.assert_not_called()

    @override_settings(EMAIL_CONFIRMATION_EXPIRE_DAYS=EXPIRE_DAYS)
    def test_confirm_on_expired_confirmation_returns_none(self):
        issuer: Issuer = IssuerFactory(email_verified=False)
        email_confirmation = IssuerEmailConfirmation.objects.create(
            issuer=issuer, sent=now() - timedelta(days=self.EXPIRE_DAYS + 3)
        )

        with patch("aidants_connect_habilitation.models.Issuer.save") as mock_save:
            self.assertFalse(issuer.email_verified)
            self.assertIs(email_confirmation.confirm(), None)
            self.assertFalse(issuer.email_verified)
            mock_save.assert_not_called()

    @patch("aidants_connect_habilitation.models.email_confirmation_sent.send")
    @freeze_time(NOW)
    def test_send(self, send_mock: Mock):
        email_confirmation = IssuerEmailConfirmation.for_issuer(
            IssuerFactory(email_verified=False)
        )
        request = HttpRequest()

        self.assertIs(email_confirmation.sent, None)
        email_confirmation.send(request)
        self.assertEqual(email_confirmation.sent, self.NOW)
        send_mock.assert_called_with(
            IssuerEmailConfirmation, request=request, confirmation=email_confirmation
        )

    @override_settings(
        EMAIL_CONFIRMATION_EXPIRE_DAYS_EMAIL_FROM=EMAIL_FROM,
        EMAIL_CONFIRMATION_EXPIRE_DAYS_EMAIL_SUBJECT=EMAIL_SUBJECT,
    )
    @patch("aidants_connect_habilitation.signals.send_mail")
    def test_signal_sends_mail(self, send_mail_mock: Mock):
        email_confirmation = IssuerEmailConfirmation.for_issuer(
            IssuerFactory(email_verified=False)
        )
        request = HttpRequest()
        request.META["SERVER_NAME"] = "localhost"
        request.META["SERVER_PORT"] = "3000"

        email_confirmation.send(request)
        send_mail_mock.assert_called_with(
            from_email=self.EMAIL_FROM,
            recipient_list=[email_confirmation.issuer.email],
            subject=self.EMAIL_SUBJECT,
            message=ANY,
            html_message=ANY,
        )


class TestIssuer(TestCase):
    def test_email_lower(self):
        data = model_to_dict(IssuerFactory.build(email="TEST@TEST.TEST"))
        issuer = Issuer.objects.create(**data)
        self.assertEqual("test@test.test", issuer.email)


class TestManager(TestCase):
    def test_email_lower(self):
        data = model_to_dict(ManagerFactory.build(email="TEST@TEST.TEST"))
        issuer = Manager.objects.create(**data)
        self.assertEqual("test@test.test", issuer.email)


class TestAidantRequest(TestCase):
    def test_email_lower(self):
        orga = OrganisationRequestFactory()
        data = model_to_dict(AidantRequestFactory.build(email="TEST@TEST.TEST"))
        issuer = AidantRequest.objects.create(**{**data, "organisation": orga})
        self.assertEqual("test@test.test", issuer.email)
