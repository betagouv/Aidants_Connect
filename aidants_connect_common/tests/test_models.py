from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.test import TestCase, override_settings, tag
from django.utils.timezone import now

from aidants_connect_common.models import (
    Formation,
    FormationAttendant,
    FormationOrganization,
    FormationType,
)
from aidants_connect_common.tests.factories import (
    FormationFactory,
    FormationOrganizationFactory,
)
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.tests.factories import (
    HabilitationRequestFactory,
    OrganisationFactory,
)


@tag("models")
@override_settings(
    TIMEDELTA_IN_DAYS_FOR_INSCRIPTION=12,
    SHORT_TIMEDELTA_IN_DAYS_FOR_INSCRIPTION=4,
    SHORT_TIMEDELTA_ATTENDANTS_COUNT_FOR_INSCRIPTION=1,
)
class FormationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        conum_type, _ = FormationType.objects.get_or_create(
            pk=settings.PK_MEDNUM_FORMATION_TYPE, label="MedNum Formation Type"
        )

        other_type, _ = FormationType.objects.get_or_create(
            pk=settings.PK_MEDNUM_FORMATION_TYPE + 1, label="Other Formation Type"
        )
        cls.other_type = other_type
        organisation = OrganisationFactory()

        FormationFactory(
            type_label="Des formations et des Hommes",
            start_datetime=now() + timedelta(days=50),
            type=other_type,
        )

        FormationFactory(
            type_label="Des formations et des Hommes",
            start_datetime=now() + timedelta(days=50),
            type=conum_type,
        )

        FormationFactory(
            type_label="Des formations et des Hommes",
            start_datetime=now() + timedelta(days=50),
            type=conum_type,
            state=Formation.State.CANCELLED,
        )

        cls.hab = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_PROCESSING,
            organisation=organisation,
            conseiller_numerique=False,
        )

        cls.hab_conum = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_PROCESSING,
            organisation=organisation,
            conseiller_numerique=True,
        )

    def test_conum_can_only_subscribe_conum_formations(self):
        self.assertEqual(
            Formation.objects.available_for_attendant(self.hab_conum).count(),
            1,
        )

    def test_can_create_one_day_formation(self):
        self.assertEqual(3, Formation.objects.all().count())
        FormationFactory(
            type_label="Formation in one day",
            start_datetime=now() + timedelta(days=50),
            end_datetime=now() + timedelta(days=50),
            type=self.other_type,
        )
        self.assertEqual(4, Formation.objects.all().count())

    def test_aidant_can_subscribe_all_formations(self):
        # Total formations count
        self.assertEqual(Formation.objects.count(), 3)

        # Formation available for attendant
        self.assertEqual(Formation.objects.available_for_attendant(self.hab).count(), 2)

    def test_display_formations_with_few_registered(self):
        # Total formations count
        self.assertEqual(Formation.objects.count(), 3)
        self.assertEqual(Formation.objects.available_for_attendant(self.hab).count(), 2)

        with self.subTest(
            f"Not showing formations starting in less than "
            f"{settings.SHORT_TIMEDELTA_IN_DAYS_FOR_INSCRIPTION} days"
        ):
            with transaction.atomic():
                FormationFactory(
                    type_label="Formation in one day",
                    start_datetime=now()
                    + timedelta(
                        days=settings.SHORT_TIMEDELTA_IN_DAYS_FOR_INSCRIPTION - 1
                    ),
                    type=self.other_type,
                )
                self.assertEqual(
                    Formation.objects.available_for_attendant(self.hab).count(), 2
                )

        with self.subTest(
            f"Not showing formations starting in less than "
            f"{settings.TIMEDELTA_IN_DAYS_FOR_INSCRIPTION} days with few registered"
        ):
            with transaction.atomic():
                FormationFactory(
                    type_label="Formation in one day",
                    start_datetime=now()
                    + timedelta(
                        days=settings.SHORT_TIMEDELTA_IN_DAYS_FOR_INSCRIPTION + 1
                    ),
                    type=self.other_type,
                )
                self.assertEqual(
                    Formation.objects.available_for_attendant(self.hab).count(), 3
                )

        with self.subTest(
            f"Not showing formations starting in more than "
            f"{settings.TIMEDELTA_IN_DAYS_FOR_INSCRIPTION} "
            f"days with a enough registered"
        ):
            with transaction.atomic():
                form: Formation = FormationFactory(
                    type_label="Formation in one day",
                    start_datetime=now()
                    + timedelta(
                        days=settings.SHORT_TIMEDELTA_IN_DAYS_FOR_INSCRIPTION + 1
                    ),
                    type=self.other_type,
                )
                for _ in range(
                    settings.SHORT_TIMEDELTA_ATTENDANTS_COUNT_FOR_INSCRIPTION + 2
                ):
                    form.register_attendant(HabilitationRequestFactory())
                self.assertEqual(
                    Formation.objects.available_for_attendant(self.hab).count(), 3
                )


class TestFormationOrganization(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_without_attendants = FormationOrganizationFactory()

        cls.org_with_warned_attendants = FormationOrganizationFactory()
        form = FormationFactory(organisation=cls.org_with_warned_attendants)
        FormationAttendant.objects.create(
            attendant=HabilitationRequestFactory(),
            formation=form,
            organization_warned_at=now(),
        )
        FormationAttendant.objects.create(
            attendant=HabilitationRequestFactory(),
            formation=form,
            organization_warned_at=now(),
        )

        cls.org_with_not_warned_attendants = FormationOrganizationFactory()
        form = FormationFactory(organisation=cls.org_with_not_warned_attendants)
        FormationAttendant.objects.create(
            attendant=HabilitationRequestFactory(),
            formation=form,
            organization_warned_at=now(),
        )
        FormationAttendant.objects.create(
            attendant=HabilitationRequestFactory(),
            formation=form,
            organization_warned_at=now(),
        )

        form = FormationFactory(organisation=cls.org_with_not_warned_attendants)
        FormationAttendant.objects.create(
            attendant=HabilitationRequestFactory(),
            formation=form,
            organization_warned_at=None,
        )
        FormationAttendant.objects.create(
            attendant=HabilitationRequestFactory(),
            formation=form,
            organization_warned_at=None,
        )

    def test_warnable_about_new_attendants(self):
        self.assertEqual(
            {self.org_with_not_warned_attendants},
            set(FormationOrganization.objects.warnable_about_new_attendants()),
        )
