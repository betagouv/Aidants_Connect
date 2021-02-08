from datetime import timedelta

from django.test import tag, TestCase
from django.test.client import Client
from django.urls import resolve
from django.utils import timezone

from aidants_connect_web.models import Autorisation

from aidants_connect_web.tests.factories import (
    OrganisationFactory,
    AidantFactory,
    AutorisationFactory,
    MandatFactory,
    UsagerFactory,
)
from aidants_connect_web.views import usagers


@tag("usagers", "revoke")
class AutorisationCancelationConfirmPageTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.our_organisation = OrganisationFactory()
        self.our_aidant = AidantFactory(organisation=self.our_organisation)
        self.our_usager = UsagerFactory()

        valid_mandat = MandatFactory(
            organisation=self.our_organisation,
            usager=self.our_usager,
        )
        self.valid_autorisation = AutorisationFactory(
            mandat=valid_mandat, demarche="Revenus"
        )
        self.revoked_autorisation = AutorisationFactory(
            mandat=valid_mandat, demarche="Papiers", revocation_date=timezone.now()
        )

        expired_mandat = MandatFactory(
            organisation=self.our_organisation,
            usager=self.our_usager,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        self.expired_autorisation = AutorisationFactory(
            mandat=expired_mandat, demarche="Logement"
        )

        self.other_organisation = OrganisationFactory(name="Other Organisation")
        self.unrelated_usager = UsagerFactory()

        unrelated_mandat = MandatFactory(
            organisation=self.other_organisation,
            usager=self.unrelated_usager,
        )
        self.unrelated_autorisation = AutorisationFactory(
            mandat=unrelated_mandat, demarche="Revenus"
        )

        mandat_other_org_with_our_usager = MandatFactory(
            organisation=self.other_organisation,
            usager=self.our_usager,
        )

        self.autorisation_other_org_with_our_usager = AutorisationFactory(
            mandat=mandat_other_org_with_our_usager, demarche="Logement"
        )

        self.good_combo = {
            "usager": self.our_usager.id,
            "autorisation": self.valid_autorisation.id,
        }

    def url_for_autorisation_cancelation_confimation(self, data):
        return (
            f"/usagers/{data['usager']}"
            f"/autorisations/{data['autorisation']}/cancel_confirm"
        )

    def test_url_triggers_the_correct_view(self):
        found = resolve(
            self.url_for_autorisation_cancelation_confimation(self.good_combo)
        )
        self.assertEqual(found.func, usagers.confirm_autorisation_cancelation)

    def test_get_triggers_the_correct_template(self):
        self.client.force_login(self.our_aidant)

        response_to_get_request = self.client.get(
            self.url_for_autorisation_cancelation_confimation(self.good_combo)
        )
        self.assertTemplateUsed(
            response_to_get_request,
            "aidants_connect_web/confirm_autorisation_cancelation.html",
        )

    def test_complete_post_triggers_redirect(self):
        self.client.force_login(self.our_aidant)

        response_correct_confirm_form = self.client.post(
            self.url_for_autorisation_cancelation_confimation(self.good_combo),
            data={"csrfmiddlewaretoken": "coucou"},
        )
        url = f"/usagers/{self.our_usager.id}/"
        self.assertRedirects(
            response_correct_confirm_form, url, fetch_redirect_response=False
        )

    def test_incomplete_post_triggers_error(self):
        self.client.force_login(self.our_aidant)
        response_incorrect_confirm_form = self.client.post(
            self.url_for_autorisation_cancelation_confimation(self.good_combo),
            data={},
        )
        self.assertTemplateUsed(
            response_incorrect_confirm_form,
            "aidants_connect_web/confirm_autorisation_cancelation.html",
        )

    def error_case_tester(self, data):
        self.client.force_login(self.our_aidant)
        response = self.client.get(
            self.url_for_autorisation_cancelation_confimation(data)
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
