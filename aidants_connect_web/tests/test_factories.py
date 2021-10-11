from django.test import tag, TestCase

from aidants_connect_web.models import (
    Aidant,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    HabilitationRequestFactory,
)


@tag("factories")
class AidantFactoryTests(TestCase):
    def test_email_and_username_generation(self):
        aidant_a = AidantFactory()
        aidant_b = AidantFactory()
        self.assertNotEqual(aidant_a.email, aidant_b.email)
        self.assertEqual(aidant_a.email, aidant_a.username)

    def test_freeze_username_freezes_email(self):
        aidant = AidantFactory(username="alban.gulhar@lovejs.org")
        self.assertEqual(aidant.email, aidant.username)
        self.assertEqual(aidant.email, "alban.gulhar@lovejs.org")

    def test_fill_database(self):
        self.assertEqual(0, len(Aidant.objects.all()))
        for count in range(1, 4):
            AidantFactory()
            self.assertEqual(count, len(Aidant.objects.all()))


@tag("factories")
class CarteTotpFactoryTests(TestCase):
    def test_sn_generation_and_seed_generation(self):
        card_1 = CarteTOTPFactory()
        card_2 = CarteTOTPFactory()
        self.assertNotEqual(card_1.serial_number, card_2.serial_number)
        self.assertNotEqual(card_1.seed, card_2.seed)


@tag("factories")
class HabilitationRequestFactoryTests(TestCase):
    def test_email_generation(self):
        hr_1 = HabilitationRequestFactory()
        hr_2 = HabilitationRequestFactory()
        self.assertNotEqual(hr_1.email, hr_2.email)
