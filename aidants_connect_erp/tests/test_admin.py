from django.contrib.admin.sites import AdminSite
from django.test import TestCase, tag
from django.test.client import RequestFactory

from ..admin import CardSendingAdmin
from ..constants import SendingStatusChoices
from ..models import CardSending
from .factories import CardSendingFactory


@tag("admin")
class CardSendingAdminTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.card_sending_admin = CardSendingAdmin(CardSending, AdminSite())

    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()
        CardSendingFactory(status=SendingStatusChoices.PREPARING)
        CardSendingFactory(status=SendingStatusChoices.PREPARING)
        CardSendingFactory(status=SendingStatusChoices.PREPARING)
        CardSendingFactory(status=SendingStatusChoices.SENDING)
        CardSendingFactory(status=SendingStatusChoices.SENDING)
        CardSendingFactory(status=SendingStatusChoices.RECEIVED)
        CardSendingFactory(status=SendingStatusChoices.RECEIVED)
        CardSendingFactory(status=SendingStatusChoices.RECEIVED)

    def test_set_in_received_state(self):
        self.assertEqual(
            3, CardSending.objects.filter(status=SendingStatusChoices.RECEIVED).count()
        )
        self.assertEqual(
            2, CardSending.objects.filter(status=SendingStatusChoices.SENDING).count()
        )

        self.card_sending_admin.set_in_received_state(
            self.rf.get("/"),
            CardSending.objects.filter(status=SendingStatusChoices.SENDING),
            False,
        )

        self.assertEqual(
            5, CardSending.objects.filter(status=SendingStatusChoices.RECEIVED).count()
        )
        self.assertEqual(
            0, CardSending.objects.filter(status=SendingStatusChoices.SENDING).count()
        )

    def test_set_in_preparing_state(self):
        self.assertEqual(
            3, CardSending.objects.filter(status=SendingStatusChoices.PREPARING).count()
        )
        self.assertEqual(
            2, CardSending.objects.filter(status=SendingStatusChoices.SENDING).count()
        )

        self.card_sending_admin.set_in_preparing_state(
            self.rf.get("/"),
            CardSending.objects.filter(status=SendingStatusChoices.SENDING),
            False,
        )

        self.assertEqual(
            5, CardSending.objects.filter(status=SendingStatusChoices.PREPARING).count()
        )
        self.assertEqual(
            0, CardSending.objects.filter(status=SendingStatusChoices.SENDING).count()
        )

    def test_set_in_sending_state(self):
        self.assertEqual(
            3, CardSending.objects.filter(status=SendingStatusChoices.PREPARING).count()
        )
        self.assertEqual(
            2, CardSending.objects.filter(status=SendingStatusChoices.SENDING).count()
        )

        self.card_sending_admin.set_in_sending_state(
            self.rf.get("/"),
            CardSending.objects.filter(status=SendingStatusChoices.PREPARING),
            False,
        )

        self.assertEqual(
            5, CardSending.objects.filter(status=SendingStatusChoices.SENDING).count()
        )
        self.assertEqual(
            0, CardSending.objects.filter(status=SendingStatusChoices.PREPARING).count()
        )
