from django.conf import settings
from django.test import TestCase, tag
from django.utils.timezone import now

from aidants_connect_common.models import Commune, Department, Region
from aidants_connect_common.utils.constants import JournalActionKeywords
from aidants_connect_web.models import (
    Aidant,
    AidantStatistiques,
    AidantStatistiquesbyDepartment,
    AidantStatistiquesbyRegion,
    HabilitationRequest,
)
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


@tag("statistics")
class AllStatisticsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.region_one = Region.objects.create(insee_code="91", name="Region 1")
        cls.region_two = Region.objects.create(insee_code="92", name="Region 2")
        cls.dep_11 = Department.objects.create(
            insee_code="911", region=cls.region_one, name="Dep 911"
        )
        cls.dep_12 = Department.objects.create(
            insee_code="912", region=cls.region_one, name="Dep 912"
        )

        cls.dep_21 = Department.objects.create(
            insee_code="921", region=cls.region_two, name="Dep 921"
        )

        cls.commune_11 = Commune.objects.create(
            insee_code="91100", name="Com 911", zrr=False, department=cls.dep_11
        )

        cls.commune_12 = Commune.objects.create(
            insee_code="91200", name="Com 911", zrr=True, department=cls.dep_11
        )

        cls.commune_21 = Commune.objects.create(
            insee_code="92100", name="Com 911", zrr=False, department=cls.dep_11
        )

        staf_orga = OrganisationFactory(name=settings.STAFF_ORGANISATION_NAME)
        orga_11 = OrganisationFactory(
            name="CCAS",
            department_insee_code="911",
            city_insee_code=cls.commune_11.insee_code,
        )
        orga_12 = OrganisationFactory(
            name="Orga dep 12",
            department_insee_code="912",
            city_insee_code=cls.commune_12.insee_code,
        )
        orga_21 = OrganisationFactory(
            name="Orga dep 21",
            department_insee_code="921",
            city_insee_code=cls.commune_21.insee_code,
        )
        # nb = 0
        AidantFactory(organisation=staf_orga)
        # nb = 0
        AidantFactory(is_active=False, organisation=orga_12)
        # nb = 1
        AidantFactory(organisation=orga_21)
        # nb = 2
        ad_with_totp = AidantFactory()
        CarteTOTPFactory(aidant=ad_with_totp)

        # nb = 3
        AidantFactory(
            post__with_otp_device=True,
            organisation=orga_11,
            can_create_mandats=False,
            post__is_organisation_manager=True,
        )
        cls.orga_ad_dep_12 = OrganisationFactory(
            name="FService AD 2", department_insee_code="912"
        )
        cls.orga_ad_dep_11 = OrganisationFactory(
            name="FService AD 3", department_insee_code="911"
        )

        cls.orga_ad_dep_21 = OrganisationFactory(
            name="FService Autre", department_insee_code="921"
        )

        cls.ad_with_totp_dep12 = AidantFactory(
            last_login=now(), organisation=cls.orga_ad_dep_12
        )
        CarteTOTPFactory(aidant=cls.ad_with_totp_dep12)

        cls.ad_with_totp_dep_11 = AidantFactory(
            last_login=now(), organisation=cls.orga_ad_dep_11
        )
        CarteTOTPFactory(aidant=cls.ad_with_totp_dep_11)

        cls.ad_with_totp_dep_21 = AidantFactory(
            last_login=now(), organisation=cls.orga_ad_dep_21
        )
        CarteTOTPFactory(aidant=cls.ad_with_totp_dep_21)

        AttestationJournalFactory(
            aidant=cls.ad_with_totp_dep_11,
            organisation=cls.ad_with_totp_dep_11.organisation,
        )

        AttestationJournalFactory(
            aidant=cls.ad_with_totp_dep_11,
            organisation=cls.ad_with_totp_dep_11.organisation,
        )

        AttestationJournalFactory(
            aidant=cls.ad_with_totp_dep12,
            organisation=cls.ad_with_totp_dep12.organisation,
        )

        JournalFactory(
            organisation=cls.ad_with_totp_dep_21.organisation,
            aidant=cls.ad_with_totp_dep_21,
            action=JournalActionKeywords.USE_AUTORISATION,
        )

        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_VALIDATED,
            formation_done=True,
            organisation=orga_11,
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_REFUSED,
            formation_done=True,
            organisation=orga_11,
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_NEW,
            formation_done=True,
            organisation=orga_11,
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_NEW,
            formation_done=True,
            organisation=orga_12,
        )
        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_NEW,
            formation_done=True,
            organisation=orga_12,
        )

        HabilitationRequestFactory(
            status=HabilitationRequest.STATUS_NEW, organisation=orga_21
        )

    def test_global_computing_new_statistics(self):
        stats = compute_statistics(AidantStatistiques())

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 2)
        self.assertEqual(stats.number_operational_aidants, 4)
        self.assertEqual(stats.number_future_aidant, 4)
        self.assertEqual(stats.number_future_trained_aidant, 4)
        self.assertEqual(stats.number_trained_aidant_since_begining, 6)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 4)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 3)

        self.assertEqual(stats.number_orgas_in_zrr, 1)
        self.assertEqual(stats.number_aidants_in_zrr, 1)

    def test_by_department_computing_new_statistics(self):
        stats = compute_statistics(
            AidantStatistiquesbyDepartment(departement=self.dep_11)
        )

        self.assertEqual(stats.number_aidants, 2)
        self.assertEqual(stats.number_aidants_is_active, 2)
        self.assertEqual(stats.number_responsable, 1)

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 1)
        self.assertEqual(stats.number_operational_aidants, 1)
        self.assertEqual(stats.number_future_aidant, 1)
        self.assertEqual(stats.number_future_trained_aidant, 2)
        self.assertEqual(stats.number_trained_aidant_since_begining, 1)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 1)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 1)

        self.assertEqual(stats.number_orgas_in_zrr, 0)
        self.assertEqual(stats.number_aidants_in_zrr, 0)

        stats = compute_statistics(
            AidantStatistiquesbyDepartment(departement=self.dep_12)
        )

        self.assertEqual(stats.number_aidants, 2)
        self.assertEqual(stats.number_aidants_is_active, 1)
        self.assertEqual(stats.number_responsable, 0)

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 1)
        self.assertEqual(stats.number_operational_aidants, 1)
        self.assertEqual(stats.number_future_aidant, 2)
        self.assertEqual(stats.number_future_trained_aidant, 2)
        self.assertEqual(stats.number_trained_aidant_since_begining, 2)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 1)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 1)

        self.assertEqual(stats.number_orgas_in_zrr, 1)
        self.assertEqual(stats.number_aidants_in_zrr, 1)

    def test_by_region_computing_new_statistics(self):
        stats = compute_statistics(AidantStatistiquesbyRegion(region=self.region_one))

        self.assertEqual(stats.number_aidants, 4)
        self.assertEqual(stats.number_aidants_is_active, 3)
        self.assertEqual(stats.number_responsable, 1)

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 2)
        self.assertEqual(stats.number_operational_aidants, 2)
        self.assertEqual(stats.number_future_aidant, 3)
        self.assertEqual(stats.number_future_trained_aidant, 4)
        self.assertEqual(stats.number_trained_aidant_since_begining, 3)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 2)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 2)

        self.assertEqual(stats.number_orgas_in_zrr, 1)
        self.assertEqual(stats.number_aidants_in_zrr, 1)

        stats = compute_statistics(AidantStatistiquesbyRegion(region=self.region_two))

        self.assertEqual(stats.number_aidants, 2)
        self.assertEqual(stats.number_aidants_is_active, 2)
        self.assertEqual(stats.number_responsable, 0)

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 0)
        self.assertEqual(stats.number_operational_aidants, 1)
        self.assertEqual(stats.number_future_aidant, 1)
        self.assertEqual(stats.number_future_trained_aidant, 0)
        self.assertEqual(stats.number_trained_aidant_since_begining, 2)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 1)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 1)

        self.assertEqual(stats.number_orgas_in_zrr, 0)
        self.assertEqual(stats.number_aidants_in_zrr, 0)
