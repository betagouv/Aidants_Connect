from datetime import timedelta

from django.test import tag, TestCase
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)

from aidants_connect_web.views.usagers import _get_mandats_for_usagers_index
from aidants_connect_web.views.usagers import _get_usagers_dict_from_mandats


@tag("usagers")
class ViewAutorisationsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant = AidantFactory()
        device = cls.aidant.staticdevice_set.create(id=cls.aidant.id)
        device.token_set.create(token="123456")

        cls.usager_alice = UsagerFactory(given_name="Alice", family_name="Lovelace")
        cls.usager_josephine = UsagerFactory(
            given_name="Joséphine", family_name="Dupont"
        )
        cls.usager_corentin = UsagerFactory(
            given_name="Corentin", family_name="Dupont", preferred_username="Astro"
        )

        cls.mandat_aidant_alice_no_autorisation = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_alice,
            expiration_date=timezone.now() + timedelta(days=5),
        )

        cls.mandat_aidant_josephine_6 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_josephine_6,
            demarche="social",
        )

        cls.mandat_aidant_josephine_1 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=1),
        )

        AutorisationFactory(
            mandat=cls.mandat_aidant_josephine_1,
            demarche="papiers",
        )

        cls.mandat_aidant_corentin_365 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_corentin,
            expiration_date=timezone.now() + timedelta(days=365),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_corentin_365,
            demarche="famille",
        )

        cls.mandat_inactif_aidant_corentin = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_corentin,
            expiration_date=timezone.now() - timedelta(days=2),
        )
        AutorisationFactory(
            mandat=cls.mandat_inactif_aidant_corentin,
            demarche="famille",
        )

        super().setUpClass()

    def test__get_mandats_for_usagers_index(self):
        mandats = _get_mandats_for_usagers_index(self.aidant)
        self.assertEqual(
            list(mandats),
            [
                self.mandat_inactif_aidant_corentin,
                self.mandat_aidant_corentin_365,
                self.mandat_aidant_josephine_1,
                self.mandat_aidant_josephine_6,
                self.mandat_aidant_alice_no_autorisation,
            ],
        )

    def test__get_usagers_dict_from_mandats(self):
        mandats = _get_mandats_for_usagers_index(self.aidant)
        usagers = _get_usagers_dict_from_mandats(mandats)
        self.assertEqual(3, len(usagers))
        usager, autorisations = usagers.popitem(last=False)
        self.assertEqual(usager, self.usager_corentin)
        self.assertEqual(
            autorisations,
            [
                (
                    "famille",
                    self.mandat_inactif_aidant_corentin.expiration_date,
                    self.mandat_inactif_aidant_corentin.expiration_date,
                ),
                ("famille", False, False),
            ],
        )

        usager, autorisations = usagers.popitem(last=False)
        self.assertEqual(usager, self.usager_josephine)
        self.assertEqual(
            autorisations,
            [
                ("papiers", False, self.mandat_aidant_josephine_1.expiration_date),
                ("social", False, self.mandat_aidant_josephine_6.expiration_date),
            ],
        )

        usager, autorisations = usagers.popitem(last=False)
        self.assertEqual(usager, self.usager_alice)
        self.assertEqual(autorisations, [])
