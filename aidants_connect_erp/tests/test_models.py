from django.test import TestCase, tag

from aidants_connect_web.tests.factories import OrganisationFactory

from ..constants import SendingStatusChoices
from ..models import CardSending


@tag("models")
class CardSendingModelTests(TestCase):
    def test_create_card_sending(self):
        orga = OrganisationFactory()
        card_sending = CardSending(
            organisation=orga,
            quantity=12,
            status=SendingStatusChoices.PREPARING.name,
        )
        card_sending.save()
        self.assertEqual(12, card_sending.quantity)
        self.assertEqual(orga, card_sending.organisation)
        self.assertEqual(SendingStatusChoices.PREPARING.name, card_sending.status)
