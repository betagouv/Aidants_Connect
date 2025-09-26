from unittest import skip

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.forms import AidantRequestForm, AidantRequestFormSet
from aidants_connect_habilitation.models import AidantRequest, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    OrganisationRequestFactory,
)
from aidants_connect_habilitation.tests.utils import get_form
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.tests.factories import HabilitationRequestFactory


@tag("functional", "habilitation")
class AddAidantsRequestViewTests(FunctionalTestCase):
    def setUp(self):
        self.add_aidant_css = "#add-aidants-btn"
        self.submit_css = "[data-test='submit']"

    def test_add_aidant_button_shown_in_readonly_view_under_correct_conditions(self):
        unauthorized_statuses = set(RequestStatusConstants) - set(
            RequestStatusConstants.aidant_registrable
        )

        for status in unauthorized_statuses:
            organisation: OrganisationRequest = OrganisationRequestFactory(
                status=status
            )
            self.__open_readonly_view_url(organisation)
            self.assertElementNotFound(By.CSS_SELECTOR, self.add_aidant_css)

        for status in RequestStatusConstants.aidant_registrable:
            with self.subTest(status):
                organisation: OrganisationRequest = OrganisationRequestFactory(
                    status=status
                )
                self.__open_readonly_view_url(organisation)
                self.check_accessibility("habilitation_organisation_view", strict=True)
                self.selenium.find_element(By.CSS_SELECTOR, self.add_aidant_css).click()

                self.wait.until(
                    self.path_matches(
                        "habilitation_new_aidants",
                        kwargs={
                            "issuer_id": str(organisation.issuer.issuer_id),
                            "uuid": str(organisation.uuid),
                        },
                    )
                )

    def test_can_correctly_add_new_aidants(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW, post__aidants_count=2
        )
        nb_aidant_requests = organisation.aidant_requests.count()
        self.assertEqual(nb_aidant_requests, 2)

        self.__open_form_url(organisation)

        formset = AidantRequestFormSet(organisation=organisation)
        for i in range(nb_aidant_requests, nb_aidant_requests + 2):
            aidant_form = get_form(
                AidantRequestForm,
                form_init_kwargs={
                    "organisation": organisation,
                    "auto_id": formset.auto_id,
                    "prefix": formset.add_prefix(i),
                },
            )
            self.fill_form(aidant_form.cleaned_data, aidant_form)
            self.selenium.find_element(By.CSS_SELECTOR, "#partial-submit").click()
            self.wait.until(
                expected_conditions.visibility_of_element_located(
                    (By.ID, f"profile-edit-card-{i}")
                )
            )

        self.selenium.find_element(By.CSS_SELECTOR, self.submit_css).click()

        self.wait.until(
            self.path_matches(
                "habilitation_validation",
                kwargs={
                    "issuer_id": str(organisation.issuer.issuer_id),
                    "uuid": str(organisation.uuid),
                },
            )
        )

        organisation.refresh_from_db()
        self.assertEqual(organisation.aidant_requests.count(), 4)

    @skip
    def test_I_can_cancel_habilitation_request(self):
        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW
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

        self._try_open_modal(By.ID, f"edit-button-{ar1.pk}")

        self.selenium.find_element(By.ID, "profile-edit-suppress").click()

        self.wait.until(self._modal_closed())

        self.selenium.find_element(By.CSS_SELECTOR, self.submit_css).click()

        self.wait.until(
            self.path_matches(
                "habilitation_validation",
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
        self.wait.until(self.dsfr_ready())

    def __open_form_url(self, organisation_request: OrganisationRequest):
        self.open_live_url(
            reverse(
                "habilitation_new_aidants",
                kwargs={
                    "issuer_id": organisation_request.issuer.issuer_id,
                    "uuid": organisation_request.uuid,
                },
            )
        )

    def _modal_closed(self):
        def modal_has_no_open_attr(driver):
            try:
                with self.implicitely_wait(0.1, driver):
                    element_attribute = driver.find_element(
                        By.CSS_SELECTOR, "#main-modal"
                    ).get_attribute("open")
                return element_attribute is None
            except:  # noqa: E722
                return False

        return expected_conditions.all_of(
            expected_conditions.invisibility_of_element_located(
                (By.CSS_SELECTOR, "#main-modal")
            ),
            modal_has_no_open_attr,
        )

    def _try_open_modal(self, by, value: str):
        self._try_close_modal()
        self.js_click(by, value)
        with self.implicitely_wait(0.1):
            self.wait.until(
                expected_conditions.text_to_be_present_in_element_attribute(
                    (By.CSS_SELECTOR, "#main-modal"),
                    "open",
                    "true",
                ),
                "Modal was not opened",
            )

            self.wait.until(
                expected_conditions.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        '#main-modal input[id$="email"]',
                    )
                ),
                "Modal seems opened but form seems not visible",
            )

    def _try_close_modal(self):
        self.wait.until(self.document_loaded())
        self.wait.until(self.dsfr_ready())
        self.js_click(By.TAG_NAME, "body")
        self.wait.until(self._modal_closed(), "Modal seems to be still visible")
