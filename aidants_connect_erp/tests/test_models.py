from django.conf import settings
from django.test import TestCase, tag

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

from ..constants import SendingStatusChoices
from ..models import CardSending, get_bizdev_users
from .factories import CardSendingFactory


@tag("models")
class CardSendingModelTests(TestCase):
    def test_create_card_sending(self):
        orga = OrganisationFactory()
        card_sending = CardSending(
            organisation=orga,
            quantity=12,
            status=SendingStatusChoices.PREPARING,
        )
        card_sending.save()
        self.assertEqual(12, card_sending.quantity)
        self.assertEqual(orga, card_sending.organisation)
        self.assertEqual(SendingStatusChoices.PREPARING, card_sending.status)

    def test_get_bizdev_users(self):
        stafforg = OrganisationFactory(name=settings.STAFF_ORGANISATION_NAME)
        AidantFactory(organisation=stafforg, is_active=True, is_staff=True)
        AidantFactory(is_active=True, is_staff=True)
        AidantFactory(is_active=True)
        self.assertEqual(1, len(get_bizdev_users()))

    def test_get_cards_stock_for_one_organisation(self):
        orga = OrganisationFactory()
        orga2 = OrganisationFactory()

        CardSendingFactory(organisation=orga2)
        CardSendingFactory(quantity=12, organisation=orga)
        CardSendingFactory(quantity=5, organisation=orga)
        self.assertEqual(17, CardSending.get_cards_stock_for_one_organisation(orga))

    def test_get_cards_stock_for_one_organisation_two(self):
        orga = OrganisationFactory()

        CardSendingFactory(quantity=12, organisation=orga)
        CardSendingFactory(
            quantity=5, organisation=orga, status=SendingStatusChoices.PREPARING
        )
        self.assertEqual(12, CardSending.get_cards_stock_for_one_organisation(orga))


@tag("models")
class CardSendingModelMethodTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga_without_ref = OrganisationFactory()

        cls.orga_with_one_ref = OrganisationFactory()
        ref1 = AidantFactory(last_name="ref1", first_name="ref1", email="ref1@orga.com")
        ref1.responsable_de.add(cls.orga_with_one_ref)

        cls.orga_with_two_refs = OrganisationFactory()
        ref2 = AidantFactory(last_name="ref2", first_name="ref2", email="ref2@orga.com")

        ref1.responsable_de.add(cls.orga_with_two_refs)
        ref2.responsable_de.add(cls.orga_with_two_refs)

    def test_get_referents_info(self):
        cs_without_ref = CardSendingFactory(organisation=self.orga_without_ref)
        cs_orga_with_one_ref = CardSendingFactory(organisation=self.orga_with_one_ref)
        cs_orga_with_two_refs = CardSendingFactory(organisation=self.orga_with_two_refs)

        self.assertEqual("Pas de référent", cs_without_ref.get_referents_info())
        self.assertTrue("ref1@orga.com" in cs_orga_with_one_ref.get_referents_info())
        self.assertTrue("ref1@orga.com" in cs_orga_with_two_refs.get_referents_info())
        self.assertTrue("ref2@orga.com" in cs_orga_with_two_refs.get_referents_info())
