from datetime import timedelta

from django.test import tag, TestCase
from django.urls import reverse
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
        cls.usager_philomene = UsagerFactory(
            given_name="Philomène", family_name="Smith"
        )

        cls.mandat_aidant_phillomene = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_philomene,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_phillomene,
            demarche="social",
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
        AutorisationFactory(
            mandat=cls.mandat_aidant_josephine_6,
            demarche="papiers",
            revocation_date=timezone.now() - timedelta(days=6),
        )

        cls.mandat_aidant_josephine_1 = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=1),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_josephine_1,
            demarche="famille",
            revocation_date=timezone.now() - timedelta(days=6),
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
                self.mandat_aidant_phillomene,
            ],
        )

    def test__get_usagers_dict_from_mandats(self):
        mandats = _get_mandats_for_usagers_index(self.aidant)
        usagers = _get_usagers_dict_from_mandats(mandats)
        self.assertEqual(4, usagers["total"])
        self.assertEqual(2, usagers["with_valid_mandate_count"])
        self.assertEqual(2, usagers["without_valid_mandate_count"])
        usager, autorisations = usagers["with_valid_mandate"].popitem(last=False)
        self.assertEqual(usager, self.usager_corentin)
        self.assertEqual(
            autorisations,
            [
                ("famille", False),
            ],
        )

        usager, autorisations = usagers["with_valid_mandate"].popitem(last=False)
        self.assertEqual(usager, self.usager_josephine)
        self.assertEqual(
            autorisations,
            [
                ("papiers", self.mandat_aidant_josephine_1.expiration_date),
                ("social", self.mandat_aidant_josephine_6.expiration_date),
            ],
        )

        self.assertSetEqual(
            usagers["without_valid_mandate"], {self.usager_alice, self.usager_philomene}
        )


@tag("usagers")
class ViewCancelMandatTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aidant = AidantFactory(
            username="dupont@example.com", email="dupont@example.com"
        )
        device = cls.aidant.staticdevice_set.create(id=cls.aidant.id)
        device.token_set.create(token="123456")

        cls.usager_philomene = UsagerFactory(
            given_name="Philomène", family_name="Smith"
        )

        cls.mandat_aidant_phillomene = MandatFactory(
            organisation=cls.aidant.organisation,
            usager=cls.usager_philomene,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_aidant_phillomene,
            demarche="social",
        )
        super().setUpClass()

    def test_cancel_inactive_mandat(self):
        self.client.force_login(self.aidant)
        response = self.client.get(
            reverse(
                "confirm_mandat_cancelation", args=(self.mandat_aidant_phillomene.id,)
            )
        )
        self.assertEqual(
            response.context["usager_name"], self.usager_philomene.get_full_name()
        )
