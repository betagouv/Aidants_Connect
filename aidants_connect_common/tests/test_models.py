from datetime import timedelta

from django.conf import settings
from django.test import TestCase, tag
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
class FormationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        conum_type, _ = FormationType.objects.get_or_create(
            pk=settings.PK_MEDNUM_FORMATION_TYPE, label="MedNum Formation Type"
        )

        other_type, _ = FormationType.objects.get_or_create(
            pk=settings.PK_MEDNUM_FORMATION_TYPE + 1, label="Other Formation Type"
        )

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
            Formation.objects.available_for_attendant(
                timedelta(days=12), self.hab_conum
            ).count(),
            1,
        )

    def test_aidant_can_subscribe_all_formations(self):
        # Total formations count
        self.assertEqual(
            Formation.objects.count(),
            3,
        )

        # Formation available for attendant
        self.assertEqual(
            Formation.objects.available_for_attendant(
                timedelta(days=12), self.hab
            ).count(),
            2,
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
