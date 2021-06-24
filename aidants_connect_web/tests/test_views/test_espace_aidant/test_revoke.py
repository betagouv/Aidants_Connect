from datetime import timedelta
import datetime
import pytz

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from aidants_connect import settings
from aidants_connect_web.models import Autorisation, Mandat

from aidants_connect_web.tests.factories import (
    OrganisationFactory,
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.views import usagers


@tag("usagers", "cancel")
class AutorisationCancellationConfirmPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.our_organisation = OrganisationFactory()
        cls.our_aidant = AidantFactory(organisation=cls.our_organisation)
        cls.our_usager = UsagerFactory()

        valid_mandat = MandatFactory(
            organisation=cls.our_organisation,
            usager=cls.our_usager,
        )
        cls.valid_autorisation = AutorisationFactory(
            mandat=valid_mandat, demarche="Revenus"
        )
        cls.revoked_autorisation = AutorisationFactory(
            mandat=valid_mandat, demarche="Papiers", revocation_date=timezone.now()
        )

        expired_mandat = MandatFactory(
            organisation=cls.our_organisation,
            usager=cls.our_usager,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        cls.expired_autorisation = AutorisationFactory(
            mandat=expired_mandat, demarche="Logement"
        )

        cls.other_organisation = OrganisationFactory(name="Other Organisation")
        cls.unrelated_usager = UsagerFactory()

        unrelated_mandat = MandatFactory(
            organisation=cls.other_organisation,
            usager=cls.unrelated_usager,
        )
        cls.unrelated_autorisation = AutorisationFactory(
            mandat=unrelated_mandat, demarche="Revenus"
        )

        mandat_other_org_with_our_usager = MandatFactory(
            organisation=cls.other_organisation,
            usager=cls.our_usager,
        )

        cls.autorisation_other_org_with_our_usager = AutorisationFactory(
            mandat=mandat_other_org_with_our_usager, demarche="Logement"
        )

        cls.good_combo = {
            "usager": cls.our_usager.id,
            "autorisation": cls.valid_autorisation.id,
        }

    def url_for_autorisation_cancellation_confimation(self, data):
        return (
            f"/usagers/{data['usager']}"
            f"/autorisations/{data['autorisation']}/cancel_confirm"
        )

    def test_url_triggers_the_correct_view(self):
        found = resolve(
            self.url_for_autorisation_cancellation_confimation(self.good_combo)
        )
        self.assertEqual(found.func, usagers.confirm_autorisation_cancelation)

    def test_get_triggers_the_correct_template(self):
        self.client.force_login(self.our_aidant)

        response_to_get_request = self.client.get(
            self.url_for_autorisation_cancellation_confimation(self.good_combo)
        )
        self.assertTemplateUsed(
            response_to_get_request,
            "aidants_connect_web/mandat_auths_cancellation/"
            "confirm_autorisation_cancelation.html",
        )

    def test_complete_post_triggers_redirect(self):
        self.client.force_login(self.our_aidant)

        response_correct_confirm_form = self.client.post(
            self.url_for_autorisation_cancellation_confimation(self.good_combo),
            data={"csrfmiddlewaretoken": "coucou"},
        )
        url = (
            f"/usagers/{self.our_usager.id}/autorisations/"
            f"{self.valid_autorisation.id}/cancel_success"
        )
        self.assertRedirects(
            response_correct_confirm_form, url, fetch_redirect_response=False
        )

    def test_incomplete_post_triggers_error(self):
        self.client.force_login(self.our_aidant)
        response_incorrect_confirm_form = self.client.post(
            self.url_for_autorisation_cancellation_confimation(self.good_combo),
            data={},
        )
        self.assertTemplateUsed(
            response_incorrect_confirm_form,
            "aidants_connect_web/mandat_auths_cancellation/"
            "confirm_autorisation_cancelation.html",
        )

    def error_case_tester(self, data):
        self.client.force_login(self.our_aidant)
        response = self.client.get(
            self.url_for_autorisation_cancellation_confimation(data)
        )
        url = "/espace-aidant/"
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_non_existing_autorisation_triggers_redirect(self):
        non_existing_autorisation = Autorisation.objects.last().id + 1

        bad_combo_for_our_aidant = {
            "usager": self.our_usager.id,
            "autorisation": non_existing_autorisation,
        }

        self.error_case_tester(bad_combo_for_our_aidant)

    def test_expired_autorisation_triggers_redirect(self):
        bad_combo_for_our_aidant = {
            "usager": self.our_usager.id,
            "autorisation": self.expired_autorisation.id,
        }

        self.error_case_tester(bad_combo_for_our_aidant)

    def test_revoked_autorisation_triggers_redirect(self):
        bad_combo_for_our_aidant = {
            "usager": self.our_usager.id,
            "autorisation": self.revoked_autorisation.id,
        }

        self.error_case_tester(bad_combo_for_our_aidant)

    def test_non_existing_usager_triggers_redirect(self):
        non_existing_usager = self.unrelated_usager.id + 1

        bad_combo_for_our_aidant = {
            "usager": non_existing_usager,
            "autorisation": self.valid_autorisation.id,
        }

        self.error_case_tester(bad_combo_for_our_aidant)

    def test_wrong_usager_autorisation_triggers_redirect(self):

        bad_combo_for_our_aidant = {
            "usager": self.our_usager.id,
            "autorisation": self.unrelated_autorisation.id,
        }

        self.error_case_tester(bad_combo_for_our_aidant)

    def test_wrong_aidant_autorisation_triggers_redirect(self):
        bad_combo_for_our_aidant = {
            "usager": self.our_usager.id,
            "autorisation": self.autorisation_other_org_with_our_usager.id,
        }

        self.error_case_tester(bad_combo_for_our_aidant)


@tag("usagers", "cancel", "cancel_mandat")
class MandatCancellationConfirmPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.our_organisation = OrganisationFactory()
        cls.our_aidant = AidantFactory(organisation=cls.our_organisation)
        cls.our_usager = UsagerFactory()

        cls.valid_mandat = MandatFactory(
            organisation=cls.our_organisation,
            usager=cls.our_usager,
        )
        cls.valid_autorisation = AutorisationFactory(
            mandat=cls.valid_mandat, demarche=[*settings.DEMARCHES][0]
        )

    def test_url_triggers_the_correct_view(self):
        found = resolve(f"/mandats/{self.valid_mandat.id}/cancel_confirm")
        self.assertEqual(found.func, usagers.confirm_mandat_cancelation)

    def test_get_triggers_the_correct_template(self):
        self.client.force_login(self.our_aidant)

        response_to_get_request = self.client.get(
            f"/mandats/{self.valid_mandat.id}/cancel_confirm"
        )

        self.assertTemplateUsed(
            response_to_get_request,
            "aidants_connect_web/mandat_auths_cancellation/"
            "confirm_mandat_cancellation.html",
        )

    def test_complete_post_triggers_redirect(self):

        self.assertTrue(self.valid_mandat.is_active)

        self.client.force_login(self.our_aidant)
        response_correct_confirm_form = self.client.post(
            f"/mandats/{self.valid_mandat.id}/cancel_confirm",
            data={"csrfmiddlewaretoken": "coucou"},
        )

        self.assertRedirects(
            response_correct_confirm_form,
            f"/mandats/{self.valid_mandat.id}/cancel_success",
            fetch_redirect_response=False,
        )
        self.assertFalse(self.valid_mandat.is_active)

    def test_incomplete_post_triggers_error(self):
        self.client.force_login(self.our_aidant)
        response_incorrect_confirm_form = self.client.post(
            f"/mandats/{self.valid_mandat.id}/cancel_confirm",
            data={},
        )
        self.assertTemplateUsed(
            response_incorrect_confirm_form,
            "aidants_connect_web/mandat_auths_cancellation/"
            "confirm_mandat_cancellation.html",
        )
        self.assertIn(
            "Une erreur s'est produite lors de la révocation du mandat",
            response_incorrect_confirm_form.context["error"],
        )

    def test_know_error_cases(self):
        def error_case_tester(mandat_id):
            self.client.force_login(self.our_aidant)
            response = self.client.get(f"/mandats/{mandat_id}/cancel_confirm")
            url = "/espace-aidant/"
            self.assertRedirects(response, url, fetch_redirect_response=False)

        expired_mandat = MandatFactory(
            expiration_date=timezone.now() - timedelta(hours=6)
        )
        revoked_mandat = MandatFactory()
        AutorisationFactory(
            mandat=revoked_mandat, revocation_date=timezone.now() - timedelta(hours=6)
        )
        other_org = OrganisationFactory(name="not our organisation")
        unrelated_mandat = MandatFactory(organisation=other_org, usager=self.our_usager)
        non_existing_mandat_id = Mandat.objects.last().id + 1

        error_case_tester(non_existing_mandat_id)
        error_case_tester(expired_mandat.id)
        error_case_tester(revoked_mandat.id)
        error_case_tester(unrelated_mandat.id)


@tag("usagers", "cancel", "cancel_mandat", "attestation")
class MandatCancellationAttestationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.our_organisation = OrganisationFactory()
        cls.our_aidant = AidantFactory(organisation=cls.our_organisation)
        cls.our_usager = UsagerFactory()

        cls.valid_mandat = MandatFactory(
            organisation=cls.our_organisation,
            usager=cls.our_usager,
            creation_date=datetime.datetime(
                2021, 2, 1, 13, 12, tzinfo=pytz.timezone("Europe/Paris")
            ),
        )
        cls.valid_autorisation = AutorisationFactory(
            mandat=cls.valid_mandat, demarche="Revenus"
        )

        cls.cancelled_mandat = MandatFactory(
            organisation=cls.our_organisation,
            usager=cls.our_usager,
            creation_date=datetime.datetime(
                2021, 2, 1, 13, 12, tzinfo=pytz.timezone("Europe/Paris")
            ),
        )
        AutorisationFactory(
            mandat=cls.cancelled_mandat,
            demarche="Revenus",
            revocation_date=timezone.now() - timedelta(minutes=5),
        )

        cls.expired_mandat = MandatFactory(
            organisation=cls.our_organisation,
            usager=cls.our_usager,
            creation_date=datetime.datetime(
                2021, 2, 1, 13, 12, tzinfo=pytz.timezone("Europe/Paris")
            ),
            expiration_date=timezone.now() - timedelta(minutes=5),
        )
        AutorisationFactory(
            mandat=cls.expired_mandat,
            demarche="Revenus",
            revocation_date=timezone.now() - timedelta(minutes=5),
        )

        AutorisationFactory(
            mandat=cls.expired_mandat,
            demarche="Papiers",
        )

    def test_url_triggers_the_correct_view(self):
        found = resolve(
            f"/mandats/{self.cancelled_mandat.id}/attestation_de_revocation"
        )
        self.assertEqual(found.func, usagers.mandat_cancellation_attestation)

    def test_get_triggers_the_correct_template(self):
        self.client.force_login(self.our_aidant)

        response_to_get_request = self.client.get(
            f"/mandats/{self.cancelled_mandat.id}/attestation_de_revocation"
        )

        self.assertTemplateUsed(
            response_to_get_request,
            "aidants_connect_web/mandat_auths_cancellation/"
            "mandat_cancellation_attestation.html",
        )

    def test_template_contains_correct_information(self):
        self.client.force_login(self.our_aidant)

        response = self.client.get(
            f"/mandats/{self.cancelled_mandat.id}/attestation_de_revocation"
        )

        self.assertIn(
            b"Homer",
            response.content,
        )
        self.assertIn(b"2021", response.content)
        self.assertIn(b"HOULBEC", response.content)

    def test_mandat_with_no_cancellations_redirects(self):
        self.client.force_login(self.our_aidant)

        response = self.client.get(
            f"/mandats/{self.valid_mandat.id}/attestation_de_revocation"
        )

        self.assertRedirects(
            response,
            "/espace-aidant/",
            fetch_redirect_response=False,
        )
