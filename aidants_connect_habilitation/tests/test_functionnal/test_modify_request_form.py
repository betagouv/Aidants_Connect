from django.test import tag
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.forms import AidantRequestForm
from aidants_connect_habilitation.models import AidantRequest, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    OrganisationRequestFactory,
)
from aidants_connect_habilitation.tests.utils import get_form
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.tests.factories import HabilitationRequestFactory


@tag("functional")
class AddAidantsRequestViewTests(FunctionalTestCase):
    def test_add_aidant_button_shown_in_readonly_view_under_correct_conditions(self):
        authorized_statuses = {
            RequestStatusConstants.NEW.name,
            RequestStatusConstants.AC_VALIDATION_PROCESSING.name,
            RequestStatusConstants.VALIDATED.name,
        }

        unauthorized_statuses = set(RequestStatusConstants.values) - authorized_statuses

        for status in unauthorized_statuses:
            organisation: OrganisationRequest = OrganisationRequestFactory(
                status=status
            )
            self.__open_readonly_view_url(organisation)

            self.selenium.find_element(By.CSS_SELECTOR, ".fr-container")
            previous_timeout = self.selenium.timeouts.implicit_wait
            # Change timeout for finding elements to shorten the test
            self.selenium.implicitly_wait(0.2)

            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element(By.CSS_SELECTOR, "#add-aidants-btn")

            self.selenium.implicitly_wait(previous_timeout)

        for status in authorized_statuses:
            organisation: OrganisationRequest = OrganisationRequestFactory(
                status=status
            )
            self.__open_readonly_view_url(organisation)

            self.selenium.find_element(By.CSS_SELECTOR, "#add-aidants-btn").click()

            path = reverse(
                "habilitation_organisation_add_aidants",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            )

            WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def test_can_correctly_add_new_aidants(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW.name, post__aidants_count=2
        )

        self.assertEqual(organisation.aidant_requests.count(), 2)

        self.__open_form_url(organisation)

        for i in range(2):
            aidant_form: AidantRequestForm = get_form(
                AidantRequestForm, form_init_kwargs={"organisation": organisation}
            )
            aidant_data = aidant_form.cleaned_data
            for field_name in aidant_form.fields:
                element = self.selenium.find_element(
                    By.CSS_SELECTOR,
                    f"#id_form-{i}-{field_name}",
                )

                if "conseiller_numerique" in element.get_attribute("name"):
                    select = Select(element)
                    select.select_by_value(str(aidant_data["conseiller_numerique"]))
                else:
                    element.clear()
                    element.send_keys(aidant_data[field_name])

            self.selenium.find_element(By.CSS_SELECTOR, "#add-aidant-btn").click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_organisation_view",
            kwargs={
                "issuer_id": str(organisation.issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 4)

    def test_I_can_cancel_habilitation_request(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW.name
        )

        ar1: AidantRequest = AidantRequestFactory(organisation=organisation)
        ar2: AidantRequest = AidantRequestFactory(organisation=organisation)

        ar1.habilitation_request = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE
        )
        ar1.save()
        ar2.habilitation_request = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_VALIDATED
        )
        ar2.save()

        self.__open_readonly_view_url(organisation)

        elts = self.selenium.find_elements(
            By.CSS_SELECTOR, 'a[id*="cancel-habilitation-request"]'
        )
        self.assertEqual(1, len(elts))
        self.assertEqual(
            f"cancel-habilitation-request-{ar2.habilitation_request.pk}",
            elts[0].get_attribute("id"),
        )

        elts[0].click()
        self.wait.until(
            self.path_matches(
                "habilitation_new_aidant_cancel_habilitation_request",
                kwargs={
                    "issuer_id": organisation.issuer.issuer_id,
                    "uuid": organisation.uuid,
                    "aidant_id": ar2.pk,
                },
            )
        )
        self.selenium.find_element(By.ID, "submit-button").click()
        self.wait.until(
            self.path_matches(
                "habilitation_organisation_view",
                kwargs={
                    "issuer_id": organisation.issuer.issuer_id,
                    "uuid": organisation.uuid,
                },
            )
        )

        ar2.habilitation_request.refresh_from_db()
        self.assertEqual(
            ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE,
            ReferentRequestStatuses(ar2.habilitation_request.status),
        )

    def __open_readonly_view_url(
        self,
        organisation_request: OrganisationRequest,
    ):
        self.open_live_url(
            reverse(
                "habilitation_organisation_view",
                kwargs={
                    "issuer_id": organisation_request.issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )

    def __open_form_url(self, organisation_request: OrganisationRequest):
        self.open_live_url(
            reverse(
                "habilitation_organisation_add_aidants",
                kwargs={
                    "issuer_id": organisation_request.issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )
