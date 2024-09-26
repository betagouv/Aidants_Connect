import time

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    invisibility_of_element_located,
    presence_of_element_located,
    visibility_of_element_located,
)

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.models import AidantRequest, OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory


@tag("functional")
class ValidationRequestFormViewTests(FunctionalTestCase):

    def setUp(self):
        super().setUp()

    def test_I_can_modify_aidant(self):
        request: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW, post__aidants_count=2
        )

        self.open_live_url(
            reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": request.issuer.issuer_id,
                    "uuid": request.uuid,
                },
            )
        )

        # Modify once
        self._fill_form_with_correct_email_and_assert(request.aidant_requests.first())

        # Modify twice
        self._fill_form_with_correct_email_and_assert(request.aidant_requests.last())

        # Modify thrice
        self._fill_form_with_correct_email_and_assert(request.aidant_requests.last())

    def test_handle_errors(self):
        request: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW, post__aidants_count=2
        )

        self.open_live_url(
            reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": request.issuer.issuer_id,
                    "uuid": request.uuid,
                },
            )
        )

        aidant: AidantRequest = request.aidant_requests.first()
        new_email = request.aidant_requests.last().email
        self._open_modale(By.ID, f"edit-button-{aidant.pk}")
        email_input = self.selenium.find_element(
            By.CSS_SELECTOR, "#profile-edit-modal #id_email"
        )
        email_input.clear()
        email_input.send_keys(new_email)

        self.selenium.find_element(
            By.CSS_SELECTOR, "#profile-edit-modal #profile-edit-submit"
        ).click()

        self.wait.until(
            presence_of_element_located(
                (By.CSS_SELECTOR, "#id_email-desc-error .fr-error-text")
            )
        )

        self.assertEqual(
            f"Il y a déjà un aidant ou une aidante avec l'adresse email '{new_email}' "
            f"dans cette organisation. Chaque aidant ou aidante doit avoir son propre "
            f"e-mail nominatif.",
            self.selenium.find_element(
                By.CSS_SELECTOR, "#id_email-desc-error .fr-error-text"
            ).text,
        )

        aidant.refresh_from_db()
        self.assertNotEqual(aidant.email, new_email)

        # Now modify with a correct address
        self._fill_form_with_correct_email_and_assert(aidant)

    def test_delete(self):
        request: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW, post__aidants_count=2
        )

        self.open_live_url(
            reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": request.issuer.issuer_id,
                    "uuid": request.uuid,
                },
            )
        )

        aidant: AidantRequest = request.aidant_requests.first()
        self._open_modale(By.ID, f"edit-button-{aidant.pk}")

        self.selenium.find_element(
            By.CSS_SELECTOR, "#profile-edit-modal #profile-edit-suppress"
        ).click()

        self.wait.until(self._modal_closed)

        self.assertElementNotFound(By.ID, f"profile-edit-card-{aidant.pk}")
        self.assertEqual(
            {request.aidant_requests.last()}, set(request.aidant_requests.all())
        )

    def test_modify_issuer(self):
        request: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW, post__aidants_count=2
        )

        self.open_live_url(
            reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": request.issuer.issuer_id,
                    "uuid": request.uuid,
                },
            )
        )

        self.selenium.find_element(By.ID, "tests-issuer-edit-button").click()
        self.wait.until(
            self.path_matches(
                "habilitation_modify_issuer_on_organisation",
                kwargs={
                    "issuer_id": f"{request.issuer.issuer_id}",
                    "uuid": f"{request.uuid}",
                },
            )
        )

        for _ in range(10):
            if (new_email := self.faker.email()) != request.issuer.email:
                break
        else:
            self.fail("This shouldn't happen")

        email_input = self.selenium.find_element(By.ID, "id_email")
        email_input.clear()
        email_input.send_keys(new_email)
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        self.wait.until(
            self.path_matches(
                "habilitation_validation",
                kwargs={
                    "issuer_id": f"{request.issuer.issuer_id}",
                    "uuid": f"{request.uuid}",
                },
            )
        )

        self.assertIn(
            new_email, self.selenium.find_element(By.ID, "test-issuer-infos").text
        )

    def _fill_form_with_correct_email_and_assert(self, request: AidantRequest):
        new_email = self._get_new_valid_email(request)
        self._open_modale(By.ID, f"edit-button-{request.pk}")
        self.wait.until(
            visibility_of_element_located(
                (By.CSS_SELECTOR, "#profile-edit-modal #id_email")
            )
        )
        email_input = self.selenium.find_element(
            By.CSS_SELECTOR, "#profile-edit-modal #id_email"
        )
        email_input.clear()
        email_input.send_keys(new_email)
        self.selenium.find_element(
            By.CSS_SELECTOR, "#profile-edit-modal #profile-edit-submit"
        ).click()
        self.wait.until(self._modal_closed)

        request.refresh_from_db()
        self.assertEqual(request.email, new_email)

    def _modal_closed(self, driver):
        return invisibility_of_element_located(
            (By.CSS_SELECTOR, "#profile-edit-modal #id_email")
        )(driver)

    def _open_modale(self, by, value):
        def try_open_modal(driver):
            time.sleep(0.5)
            self.js_click(by, value)
            time.sleep(0.3)
            return visibility_of_element_located(
                (By.CSS_SELECTOR, "#profile-edit-modal #id_email")
            )(driver)

        self.wait.until(self.document_loaded())
        self.wait.until(try_open_modal)

    def _close_modale(self):
        def try_close_modale(driver):
            # Not using WebElement.click modal may not be visible (already closed)
            self.js_click(
                By.CSS_SELECTOR,
                '#profile-edit-modal [aria-controls="profile-edit-modal"]',
            )
            return self._modal_closed(driver)

        self.wait.until(self.document_loaded())
        self.wait.until(try_close_modale)

    def _get_new_valid_email(self, request: AidantRequest):
        emails = request.organisation.aidant_requests.values_list("email", flat=True)
        for _ in range(10):
            new_email = self.faker.email()
            if new_email not in emails:
                return new_email

        self.fail("This shouldn't happen")
