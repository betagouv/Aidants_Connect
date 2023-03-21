from django.conf import settings
from django.test import TestCase, tag
from django.utils.timezone import now

from aidants_connect_web.models import Aidant
from aidants_connect_web.statistics import compute_statistics
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AttestationJournalFactory,
    CarteTOTPFactory,
    OrganisationFactory,
)


@tag("statistics")
class StatisticsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        staf_orga = OrganisationFactory(name=settings.STAFF_ORGANISATION_NAME)
        orga = OrganisationFactory(name="CCAS")
        AidantFactory(organisation=staf_orga)
        AidantFactory(is_active=False)
        AidantFactory()
        ad_with_totp = AidantFactory()
        CarteTOTPFactory(aidant=ad_with_totp)

        AidantFactory(
            post__with_otp_device=True,
            organisation=orga,
            can_create_mandats=False,
            post__is_organisation_manager=True,
        )

    def test_one_compute_statistics(self):
        stats = compute_statistics()
        self.assertEqual(Aidant.objects.count(), 5)
        self.assertEqual(stats.number_aidants, 4)
        self.assertEqual(stats.number_aidants_is_active, 3)
        self.assertEqual(stats.number_responsable, 1)
        self.assertEqual(stats.number_aidant_can_create_mandat, 2)
        self.assertEqual(stats.number_aidants_without_totp, 1)
        self.assertEqual(stats.number_aidant_with_login, 0)
        self.assertEqual(stats.number_aidant_who_have_created_mandat, 0)

    def test_two_compute_statistics(self):
        self.ad_with_totp_two = AidantFactory(last_login=now())
        CarteTOTPFactory(aidant=self.ad_with_totp_two)
        self.ad_with_totp_three = AidantFactory(last_login=now())
        CarteTOTPFactory(aidant=self.ad_with_totp_three)

        AttestationJournalFactory(aidant=self.ad_with_totp_three)
        stats = compute_statistics()

        self.assertEqual(stats.number_aidants, 6)
        self.assertEqual(stats.number_aidant_with_login, 2)
        self.assertEqual(stats.number_aidant_who_have_created_mandat, 1)
