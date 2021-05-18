from random import randint
from unittest.mock import patch, Mock
from uuid import uuid4
from typing import List

import factory
from django.template.loader import render_to_string
from django.test import tag, TestCase, override_settings
from django.urls import reverse
from django.conf import settings

from phonenumbers import PhoneNumberFormat, format_number

from aidants_connect_web.constants import JournalActionKeywords
from aidants_connect_web.models import Journal
from aidants_connect_web.sms_api import SafeClient
from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.tests.test_utilities import SmsTestUtils


@tag("sms")
@override_settings(
    OVH_SMS_ENABLED=False,
    OVH_SMS_SERVICE_NAME="d59194b4-f920-460a-bc23-1b62b82b76cc",
    OVH_SMS_SENDER_ID="Aidant Connect",
)
class SmsCallbackTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant = AidantFactory(
            username=factory.Faker("name"), email=factory.Faker("email")
        )
        cls.request_no_response = Journal.log_consent_request_sent(
            aidant=cls.aidant,
            demarche=cls.__select_random_procedures(),
            duree=365,
            user_phone="0 800 840 801",
            consent_request_tag=str(uuid4()),
        )

        kwargs = {
            "aidant": cls.aidant,
            "demarche": cls.__select_random_procedures(),
            "duree": 365,
            "user_phone": "+33 800 840 802",
            "consent_request_tag": str(uuid4()),
        }
        cls.request_with_response = Journal.log_consent_request_sent(**kwargs)
        Journal.log_denial_of_consent_received(**kwargs)

        super().setUpClass()

    def test_no_corresponding_consent_request(self):
        data = SmsTestUtils.get_request_data()
        self.client.post(reverse("sms_callback"), data=data)
        self.client.post(reverse("sms_callback"), data=data)
        response = self.client.post(reverse("sms_callback"), data=data)

        query_set = Journal.find_consent_denial_or_agreement(
            data["senderid"],
            data["tag"],
        )
        self.assertEqual(query_set.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_with_corresponding_consent_denial(self):
        data = SmsTestUtils.get_request_data(
            sms_tag=self.request_with_response.consent_request_tag,
            user_phone=self.request_with_response.user_phone,
        )

        query_set = Journal.find_consent_denial_or_agreement(
            data["senderid"],
            data["tag"],
        )
        self.assertEqual(query_set.count(), 1)

        self.client.post(reverse("sms_callback"), data=data)
        self.client.post(reverse("sms_callback"), data=data)
        response = self.client.post(reverse("sms_callback"), data=data)

        query_set = Journal.find_consent_denial_or_agreement(
            data["senderid"],
            data["tag"],
        )
        self.assertEqual(query_set.count(), 1)
        self.assertEqual(response.status_code, 200)

    @patch.object(SafeClient, "delete")
    @patch.object(SafeClient, "post", side_effect=SmsTestUtils.patched_safe_client_post)
    def test_nominal_case(self, mock_post: Mock, mock_delete: Mock):
        data = SmsTestUtils.get_request_data(
            sms_tag=self.request_no_response.consent_request_tag,
            user_phone=self.request_no_response.user_phone,
        )

        query_set = Journal.find_consent_denial_or_agreement(
            data["senderid"],
            data["tag"],
        )
        self.assertEqual(query_set.count(), 0)

        response = self.client.post(reverse("sms_callback"), data=data)

        self.assertEqual(query_set.count(), 1)
        self.assertEqual(
            query_set.first().action,
            JournalActionKeywords.AGREEMENT_OF_CONSENT_RECEIVED,
        )
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_called_once_with(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}/incoming/{data['id']}"
        )
        mock_post.assert_called_once_with(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}/jobs",
            receivers=[
                format_number(
                    self.request_no_response.user_phone, PhoneNumberFormat.E164
                )
            ],
            message=render_to_string("aidants_connect_web/sms_agreement_receipt.txt"),
            sender=settings.OVH_SMS_SENDER_ID,
            senderForResponse=False,
            noStopClause=True,
            tag=self.request_no_response.consent_request_tag,
        )

        mock_delete.reset_mock()
        mock_post.reset_mock()
        response = self.client.post(reverse("sms_callback"), data=data)

        self.assertEqual(query_set.count(), 1)
        self.assertEqual(
            query_set.first().action,
            JournalActionKeywords.AGREEMENT_OF_CONSENT_RECEIVED,
        )
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_not_called()
        mock_post.assert_not_called()

    @patch.object(SafeClient, "delete")
    @patch.object(SafeClient, "post", side_effect=SmsTestUtils.patched_safe_client_post)
    def test_deny_case(self, mock_post: Mock, mock_delete: Mock):
        data = SmsTestUtils.get_request_data(
            sms_tag=self.request_no_response.consent_request_tag,
            user_phone=self.request_no_response.user_phone,
            message="Nope",
        )

        query_set = Journal.find_consent_denial_or_agreement(
            data["senderid"],
            data["tag"],
        )
        self.assertEqual(query_set.count(), 0)

        response = self.client.post(reverse("sms_callback"), data=data)

        self.assertEqual(query_set.count(), 1)
        self.assertEqual(
            query_set.first().action, JournalActionKeywords.DENIAL_OF_CONSENT_RECEIVED
        )
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_called_once_with(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}/incoming/{data['id']}"
        )
        mock_post.assert_called_once_with(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}/jobs",
            receivers=[
                format_number(
                    self.request_no_response.user_phone, PhoneNumberFormat.E164
                )
            ],
            message=render_to_string("aidants_connect_web/sms_denial_receipt.txt"),
            sender=settings.OVH_SMS_SENDER_ID,
            senderForResponse=False,
            noStopClause=True,
            tag=self.request_no_response.consent_request_tag,
        )

        mock_delete.reset_mock()
        mock_post.reset_mock()
        response = self.client.post(reverse("sms_callback"), data=data)

        self.assertEqual(query_set.count(), 1)
        self.assertEqual(
            query_set.first().action, JournalActionKeywords.DENIAL_OF_CONSENT_RECEIVED
        )
        self.assertEqual(response.status_code, 200)
        mock_delete.assert_not_called()
        mock_post.assert_not_called()

    @classmethod
    def __select_random_procedures(cls) -> List[str]:
        procedures = [*settings.DEMARCHES.keys()]
        nb = randint(1, len(procedures))
        result = []
        for _ in range(nb):
            value = procedures[randint(0, len(procedures) - 1)]
            result.append(value)
            procedures.remove(value)
        return result
