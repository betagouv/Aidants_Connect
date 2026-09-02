from datetime import datetime

from django.conf import settings
from django.test import TestCase, tag
from django.utils import timezone
from django.utils.timezone import now

from dateutil.relativedelta import relativedelta
from django_otp.plugins.otp_totp.models import TOTPDevice
from freezegun import freeze_time

from aidants_connect_common.constants import JournalActionKeywords
from aidants_connect_common.models import Commune, Department, Region
from aidants_connect_web.constants import OTP_APP_DEVICE_NAME, ReferentRequestStatuses
from aidants_connect_web.models import (
    Aidant,
    AidantStatistiques,
    AidantStatistiquesbyDepartment,
    AidantStatistiquesbyRegion,
    Journal,
    Mandat,
)
from aidants_connect_web.statistics import (
    compute_statistics,
    get_monthly_series,
    get_personnes_accompagnees_monthly_series,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AttestationJournalFactory,
    AutorisationFactory,
    CarteTOTPFactory,
    HabilitationRequestFactory,
    JournalFactory,
    MandatFactory,
    OrganisationFactory,
    UsagerFactory,
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
        cls.orga_11 = orga_11 = OrganisationFactory(
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

        # nb = 4
        AidantFactory(deactivation_warning_at=timezone.now() - relativedelta(months=6))
        # nb = 5
        AidantFactory(deactivation_warning_at=timezone.now() - relativedelta(months=6))
        # nb = 6
        AidantFactory(
            deactivation_warning_at=timezone.now() - relativedelta(months=6),
            is_active=False,
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

        a = AidantFactory(
            organisation=cls.orga_ad_dep_11,
            is_active=True,
        )
        TOTPDevice.objects.create(
            user=a,
            name=OTP_APP_DEVICE_NAME % a.pk,
            confirmed=False,
        )

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
            status=ReferentRequestStatuses.STATUS_VALIDATED.value,
            formation_done=True,
            organisation=orga_11,
        )
        HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_REFUSED.value,
            formation_done=True,
            organisation=orga_11,
        )
        HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_NEW.value,
            formation_done=True,
            organisation=orga_11,
        )
        HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_NEW.value,
            formation_done=True,
            organisation=orga_12,
        )
        HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_NEW.value,
            formation_done=True,
            organisation=orga_12,
        )

        HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_NEW.value, organisation=orga_21
        )

    def test_number_organisation_with_accredited_aidants(self):
        stats = compute_statistics(AidantStatistiques())
        self.assertEqual(stats.number_organisation_with_accredited_aidants, 4)

        new_ad = AidantFactory(last_login=now(), organisation=self.orga_ad_dep_11)
        CarteTOTPFactory(aidant=new_ad)

        nstats = compute_statistics(AidantStatistiques())
        self.assertEqual(nstats.number_organisation_with_accredited_aidants, 4)

    def test_global_computing_new_statistics(self):
        stats = compute_statistics(AidantStatistiques())

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 2)
        self.assertEqual(stats.number_operational_aidants, 4)
        self.assertEqual(stats.number_future_aidant, 4)
        self.assertEqual(stats.number_future_trained_aidant, 4)
        self.assertEqual(stats.number_trained_aidant_since_begining, 10)

        self.assertEqual(stats.number_organisation_with_accredited_aidants, 4)
        self.assertEqual(stats.number_organisation_with_at_least_one_ac_usage, 3)

        self.assertEqual(stats.number_orgas_in_zrr, 1)
        self.assertEqual(stats.number_aidants_in_zrr, 1)

        self.assertEqual(stats.number_old_inactive_aidants_warned, 1)
        self.assertEqual(stats.number_old_aidants_warned, 2)

        self.assertEqual(stats.number_aidants_with_otp_app, 1)
        self.assertEqual(stats.number_active_mandats, 0)

    def test_by_department_computing_new_statistics(self):
        stats = compute_statistics(
            AidantStatistiquesbyDepartment(departement=self.dep_11)
        )

        self.assertEqual(stats.number_aidants, 3)
        self.assertEqual(stats.number_aidants_is_active, 3)
        self.assertEqual(stats.number_responsable, 1)

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 1)
        self.assertEqual(stats.number_operational_aidants, 1)
        self.assertEqual(stats.number_future_aidant, 1)
        self.assertEqual(stats.number_future_trained_aidant, 2)
        self.assertEqual(stats.number_trained_aidant_since_begining, 2)

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

        self.assertEqual(stats.number_aidants, 5)
        self.assertEqual(stats.number_aidants_is_active, 4)
        self.assertEqual(stats.number_responsable, 1)

        self.assertEqual(stats.number_aidant_who_have_created_mandat, 2)
        self.assertEqual(stats.number_operational_aidants, 2)
        self.assertEqual(stats.number_future_aidant, 3)
        self.assertEqual(stats.number_future_trained_aidant, 4)
        self.assertEqual(stats.number_trained_aidant_since_begining, 4)

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


@tag("statistics")
class ActiveMandatsStatisticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga = OrganisationFactory()
        cls.staff_orga = OrganisationFactory(name=settings.STAFF_ORGANISATION_NAME)
        cls.usager = UsagerFactory()

        cls.active_mandat = MandatFactory(organisation=cls.orga, usager=cls.usager)
        AutorisationFactory(mandat=cls.active_mandat)

        cls.expired_mandat = MandatFactory(
            organisation=cls.orga,
            usager=UsagerFactory(),
            expiration_date=datetime(year=2000, month=1, day=1, tzinfo=timezone.utc),
        )
        AutorisationFactory(mandat=cls.expired_mandat)

        cls.staff_mandat = MandatFactory(
            organisation=cls.staff_orga, usager=UsagerFactory()
        )
        AutorisationFactory(mandat=cls.staff_mandat)

    def test_global_active_mandats_count_includes_staff_mandats(self):
        stats = compute_statistics(AidantStatistiques())
        self.assertEqual(stats.number_active_mandats, 2)

    def test_department_active_mandats_count_excludes_other_departments(self):
        region, _ = Region.objects.get_or_create(
            insee_code="99", defaults={"name": "Région test stats"}
        )
        dep, _ = Department.objects.get_or_create(
            insee_code="990",
            defaults={
                "region": region,
                "name": "Département test stats",
                "zipcode": "99000",
            },
        )
        self.orga.department_insee_code = dep.insee_code
        self.orga.save()

        stats = compute_statistics(AidantStatistiquesbyDepartment(departement=dep))
        self.assertEqual(stats.number_active_mandats, 1)


@tag("statistics")
class MandatsEvolutionStatisticsTests(TestCase):
    def test_monthly_series_counts_mandats_by_creation_month(self):
        orga = OrganisationFactory()
        usager_one = UsagerFactory()
        usager_two = UsagerFactory()

        MandatFactory(
            organisation=orga,
            usager=usager_one,
            creation_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        MandatFactory(
            organisation=orga,
            usager=usager_two,
            creation_date=datetime(2024, 2, 10, tzinfo=timezone.utc),
        )

        series = get_monthly_series(
            Mandat.objects.filter(organisation=orga), "creation_date"
        )

        self.assertEqual(series["labels"], ["01/2024", "02/2024"])
        self.assertEqual(series["values"], [1, 1])

    @freeze_time("2024-03-15 12:00:00")
    def test_monthly_series_limits_to_last_twenty_four_months(self):
        orga = OrganisationFactory()
        MandatFactory(
            organisation=orga,
            usager=UsagerFactory(),
            creation_date=datetime(2023, 3, 1, tzinfo=timezone.utc),
        )
        MandatFactory(
            organisation=orga,
            usager=UsagerFactory(),
            creation_date=datetime(2023, 4, 1, tzinfo=timezone.utc),
        )
        MandatFactory(
            organisation=orga,
            usager=UsagerFactory(),
            creation_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )

        series = get_monthly_series(
            Mandat.objects.filter(organisation=orga),
            "creation_date",
            months=24,
        )

        self.assertEqual(len(series["labels"]), 24)
        self.assertEqual(series["labels"][0], "03/2022")
        self.assertEqual(series["labels"][-1], "02/2024")
        self.assertEqual(series["values"][12], 1)
        self.assertEqual(series["values"][13], 1)
        self.assertEqual(series["values"][-1], 1)
        self.assertEqual(sum(series["values"]), 3)


@tag("statistics")
class DemarchesEvolutionStatisticsTests(TestCase):
    @freeze_time("2024-03-15 12:00:00")
    def test_monthly_series_counts_demarches_by_creation_month(self):
        orga = OrganisationFactory()
        aidant = AidantFactory(organisation=orga)
        for month in (4, 5):
            JournalFactory(
                organisation=orga,
                aidant=aidant,
                action=JournalActionKeywords.USE_AUTORISATION,
                creation_date=datetime(2023, month, 1, tzinfo=timezone.utc),
            )
        JournalFactory(
            organisation=orga,
            aidant=aidant,
            action=JournalActionKeywords.USE_AUTORISATION,
            creation_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )

        series = get_monthly_series(
            Journal.objects.filter(action=JournalActionKeywords.USE_AUTORISATION),
            "creation_date",
            months=24,
        )

        self.assertEqual(len(series["labels"]), 24)
        self.assertEqual(series["labels"][0], "03/2022")
        self.assertEqual(series["labels"][-1], "02/2024")
        self.assertEqual(series["values"][13], 1)
        self.assertEqual(series["values"][14], 1)
        self.assertEqual(series["values"][-1], 1)
        self.assertEqual(sum(series["values"]), 3)


@tag("statistics")
class PersonnesAccompagneesEvolutionStatisticsTests(TestCase):
    @freeze_time("2024-03-15 12:00:00")
    def test_counts_unique_usagers_on_first_demarche_month(self):
        orga = OrganisationFactory()
        aidant = AidantFactory(organisation=orga)
        usager_one = UsagerFactory()
        usager_two = UsagerFactory()
        usager_three = UsagerFactory()

        # First accompaniment for usager_one before the 24-month window
        JournalFactory(
            organisation=orga,
            aidant=aidant,
            usager=usager_one,
            action=JournalActionKeywords.USE_AUTORISATION,
            creation_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
        )
        # Later démarches for the same usager must not create a new "personne"
        JournalFactory(
            organisation=orga,
            aidant=aidant,
            usager=usager_one,
            action=JournalActionKeywords.USE_AUTORISATION,
            creation_date=datetime(2023, 5, 1, tzinfo=timezone.utc),
        )
        # New people during the window
        JournalFactory(
            organisation=orga,
            aidant=aidant,
            usager=usager_two,
            action=JournalActionKeywords.USE_AUTORISATION,
            creation_date=datetime(2023, 4, 1, tzinfo=timezone.utc),
        )
        JournalFactory(
            organisation=orga,
            aidant=aidant,
            usager=usager_three,
            action=JournalActionKeywords.USE_AUTORISATION,
            creation_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )

        series = get_personnes_accompagnees_monthly_series(
            Journal.objects.filter(action=JournalActionKeywords.USE_AUTORISATION),
            months=24,
        )

        self.assertEqual(len(series["labels"]), 24)
        self.assertEqual(series["labels"][0], "03/2022")
        self.assertEqual(series["labels"][-1], "02/2024")
        # Baseline includes usager_one; monthly only counts new people
        self.assertEqual(series["monthly"][13], 1)  # 04/2023 -> usager_two
        self.assertEqual(series["monthly"][14], 0)  # 05/2023 -> no new people
        self.assertEqual(series["monthly"][-1], 1)  # 02/2024 -> usager_three
        self.assertEqual(sum(series["monthly"]), 2)
        self.assertEqual(series["cumulative"][0], 1)
        self.assertEqual(series["cumulative"][-1], 3)
