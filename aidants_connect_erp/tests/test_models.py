from django.conf import settings
from django.test import TestCase, tag

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

from ..constants import SendingStatusChoices
from ..models import CardSending, get_bizdev_users


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

    def test_get_bizdev_users(self):
        stafforg = OrganisationFactory(name=settings.STAFF_ORGANISATION_NAME)
        AidantFactory(organisation=stafforg, is_active=True, is_staff=True)
        AidantFactory(is_active=True, is_staff=True)
        AidantFactory(is_active=True)
        self.assertEqual(1, len(get_bizdev_users()))
