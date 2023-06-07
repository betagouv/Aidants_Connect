from django.conf import settings
from django.test import TestCase, tag
from django.utils.timezone import now

from aidants_connect_common.utils.constants import JournalActionKeywords
from aidants_connect_web.models import Aidant, AidantStatistiques, HabilitationRequest
from aidants_connect_web.statistics import compute_statistics
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AttestationJournalFactory,
    CarteTOTPFactory,
    HabilitationRequestFactory,
    JournalFactory,
    OrganisationFactory,
)


@tag("statistics")
class StatisticsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        staf_orga = OrganisationFactory(name=settings.STAFF_ORGANISATION_NAME)
        orga = OrganisationFactory(name="CCAS")
        # nb = 0
        AidantFactory(organisation=staf_orga)
        # nb = 0
        AidantFactory(is_active=False)
        # nb = 1
        AidantFactory()
        # nb = 2
        ad_with_totp = AidantFactory()
        CarteTOTPFactory(aidant=ad_with_totp)

        # nb = 3
        AidantFactory(
            post__with_otp_device=True,
            organisation=orga,
            can_create_mandats=False,
            post__is_organisation_manager=True,
        )

    def test_one_compute_statistics(self):
        stats = compute_statistics(AidantStatistiques())
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
        stats = compute_statistics(AidantStatistiques())

        self.assertEqual(stats.number_aidants, 6)
        self.assertEqual(stats.number_aidant_with_login, 2)
        self.assertEqual(stats.number_aidant_who_have_created_mandat, 1)

    def test_computing_new_statistics(self):
        orga_ad_two = OrganisationFactory(name="FService AD 2")
        orga_ad_three = OrganisationFactory(name="FService AD 3")

        orga_ad_four = OrganisationFactory(name="FService Autre")

        self.ad_with_totp_two = AidantFactory(
            last_login=now(), organisation=orga_ad_two
        )
        CarteTOTPFactory(aidant=self.ad_with_totp_two)
        self.ad_with_totp_three = AidantFactory(
            last_login=now(), organisation=orga_ad_three
        )
        CarteTOTPFactory(aidant=self.ad_with_totp_three)

        self.ad_with_totp_four = AidantFactory(
            last_login=now(), organisation=orga_ad_four
        )
        CarteTOTPFactory(aidant=self.ad_with_totp_four)

        AttestationJournalFactory(
            aidant=self.ad_with_totp_three,
            organisation=self.ad_with_totp_three.organisation,
        )

        AttestationJournalFactory(
            aidant=self.ad_with_totp_three,
            organisation=self.ad_with_totp_three.organisation,
        )

        AttestationJournalFactory(
            aidant=self.ad_with_totp_two,
            organisation=self.ad_with_totp_two.organisation,
        )

        JournalFactory(
            organisation=orga_ad_four,
            aidant=self.ad_with_totp_four,
            action=JournalActionKeywords.USE_AUTORISATION,
        )

        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_VALIDATED, formation_done=True
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_REFUSED, formation_done=True
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_NEW, formation_done=True
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_NEW, formation_done=True
        )
        HabilitationRequestFactory(status=HabilitationRequest.STATUS_NEW)

        stats = compute_statistics(AidantStatistiques())

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 2)
        self.assertEqual(stats.number_operational_aidants, 4)
        self.assertEqual(stats.number_future_aidant, 3)
        self.assertEqual(stats.number_future_trained_aidant, 3)
        self.assertEqual(stats.number_trained_aidant_since_begining, 6)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 4)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 3)
