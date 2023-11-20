from django.test import TestCase, tag
from django.utils.timezone import now, timedelta

from aidants_connect_common.utils.constants import JournalActionKeywords
from aidants_connect_web.models import ReboardingAidantStatistiques
from aidants_connect_web.statistics.reboarding import (
    compute_reboarding_statistics_for_aidant,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    JournalFactory,
    OrganisationFactory,
    UsagerFactory,
)


@tag("statistics")
class ReboardingStatisticsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        orga = OrganisationFactory(name="CCAS")

        cls.reboarding_session_date = now() - timedelta(days=10)
        cls.cloud = AidantFactory(
            email="cloud@ccas.fr",
            organisation=orga,
            first_name="Cloud",
            last_name="Strife",
        )

        cls.jaskier = AidantFactory(
            email="jaskier@ccas.fr", organisation=orga, first_name="Jaskier"
        )

        cls.usager = UsagerFactory()
        cls.usager2 = UsagerFactory()

        # Connexion
        JournalFactory(
            action=JournalActionKeywords.CONNECT_AIDANT,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date - timedelta(days=110),
        )

        JournalFactory(
            action=JournalActionKeywords.CONNECT_AIDANT,
            aidant=cls.jaskier,
            creation_date=cls.reboarding_session_date - timedelta(days=110),
        )

        JournalFactory(
            action=JournalActionKeywords.CONNECT_AIDANT,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date + timedelta(days=20),
        )

        JournalFactory(
            action=JournalActionKeywords.CONNECT_AIDANT,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date + timedelta(days=28),
        )

        # Creation mandat
        JournalFactory(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date - timedelta(days=10),
        )

        JournalFactory(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date + timedelta(days=8),
        )

        JournalFactory(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date + timedelta(days=65),
        )

        JournalFactory(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date + timedelta(days=75),
        )

        JournalFactory(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            aidant=cls.cloud,
            creation_date=cls.reboarding_session_date + timedelta(days=115),
        )

        # Utilisation démarches
        # Accompagnement Usagers
        JournalFactory(
            action=JournalActionKeywords.USE_AUTORISATION,
            aidant=cls.cloud,
            usager=cls.usager,
            creation_date=cls.reboarding_session_date - timedelta(days=10),
        )

        JournalFactory(
            action=JournalActionKeywords.USE_AUTORISATION,
            aidant=cls.cloud,
            usager=cls.usager,
            creation_date=cls.reboarding_session_date - timedelta(days=11),
        )

        JournalFactory(
            action=JournalActionKeywords.USE_AUTORISATION,
            aidant=cls.cloud,
            usager=cls.usager,
            creation_date=cls.reboarding_session_date + timedelta(days=8),
        )

        JournalFactory(
            action=JournalActionKeywords.USE_AUTORISATION,
            aidant=cls.cloud,
            usager=cls.usager,
            creation_date=cls.reboarding_session_date + timedelta(days=65),
        )

        JournalFactory(
            action=JournalActionKeywords.USE_AUTORISATION,
            aidant=cls.cloud,
            usager=cls.usager2,
            creation_date=cls.reboarding_session_date + timedelta(days=75),
        )

        JournalFactory(
            action=JournalActionKeywords.USE_AUTORISATION,
            aidant=cls.cloud,
            usager=cls.usager,
            creation_date=cls.reboarding_session_date + timedelta(days=115),
        )

    def test_compute_reboarding_statistics_for_aidant(self):
        stats = ReboardingAidantStatistiques(
            aidant=self.cloud, reboarding_session_date=self.reboarding_session_date
        )

        stats = compute_reboarding_statistics_for_aidant(stats)

        self.assertEqual(stats.connexions_before_reboarding, 1)
        self.assertEqual(stats.connexions_j30_after, 2)
        self.assertEqual(stats.connexions_j90_after, 2)

        self.assertEqual(stats.created_mandats_before_reboarding, 1)
        self.assertEqual(stats.created_mandats_j30_after, 1)
        self.assertEqual(stats.created_mandats_j90_after, 3)

        self.assertEqual(stats.demarches_before_reboarding, 2)
        self.assertEqual(stats.demarches_j30_after, 1)
        self.assertEqual(stats.demarches_j90_after, 3)

        self.assertEqual(stats.usagers_before_reboarding, 1)
        self.assertEqual(stats.usagers_j30_after, 1)
        self.assertEqual(stats.usagers_j90_after, 2)
