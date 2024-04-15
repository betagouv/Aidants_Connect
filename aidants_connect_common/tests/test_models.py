from datetime import timedelta

from django.conf import settings
from django.test import TestCase, tag
from django.utils.timezone import now

from aidants_connect_common.models import Formation, FormationType
from aidants_connect_common.tests.factories import FormationFactory
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
        self.assertEqual(
            Formation.objects.available_for_attendant(
                timedelta(days=12), self.hab
            ).count(),
            2,
        )
