from datetime import timedelta
from unittest.mock import Mock, patch

from django.db import IntegrityError
from django.http import HttpRequest
from django.test import TestCase, override_settings, tag
from django.utils.timezone import now

from freezegun import freeze_time

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_habilitation.models import Issuer, IssuerEmailConfirmation
from aidants_connect_habilitation.tests.factories import (
    IssuerFactory,
    OrganisationRequestFactory,
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
            OrganisationRequestFactory(cgu=False, draft_id=None)
        self.assertIn("cgu_checked", str(cm.exception))

    def test_dpo_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(dpo=False, draft_id=None)
        self.assertIn("dpo_checked", str(cm.exception))

    def test_professionals_only_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(professionals_only=False, draft_id=None)
        self.assertIn("professionals_only_checked", str(cm.exception))

    def test_without_elected_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(without_elected=False, draft_id=None)
        self.assertIn("without_elected_checked", str(cm.exception))

    def test_manager_set_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(manager=None, draft_id=None)
        self.assertIn("manager_set", str(cm.exception))

    def test_data_privacy_officer_set_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(data_privacy_officer=None, draft_id=None)
        self.assertIn("data_privacy_officer_set", str(cm.exception))


class TestIssuerEmailConfirmation(TestCase):
    NOW = now()
    EXPIRE_DAYS = 3

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
