from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.models import AidantRequest, OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory


@tag("functional", "habilitation")
class ValidationRequestFormViewTests(FunctionalTestCase):
    def setUp(self):
        self.request: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW, post__aidants_count=2
        )
        self.url = reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": self.request.issuer.issuer_id,
                "uuid": self.request.uuid,
            },
        )

    def test_I_can_modify_aidant(self):
        self.open_live_url(self.url)

        # Modify once
        self._fill_form_with_correct_email_and_assert(
            self.request.aidant_requests.first()
        )

        # Modify twice
        self._fill_form_with_correct_email_and_assert(
            self.request.aidant_requests.last()
        )

        # Modify thrice
        self._fill_form_with_correct_email_and_assert(
            self.request.aidant_requests.last()
        )

    def test_handle_errors(self):
        self.open_live_url(self.url)

        aidant: AidantRequest = self.request.aidant_requests.first()
        new_email = self.request.aidant_requests.last().email
        self._try_open_modal(By.ID, f"edit-button-{aidant.pk}")
        email_input = self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #id_email"
        )
        email_input.clear()
        email_input.send_keys(new_email)

        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-submit"
        ).click()

        self.wait.until(
            expected_conditions.presence_of_element_located(
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
        self._fill_form_with_correct_email_and_assert(aidant, modal_opened=True)

    def test_delete(self):
        self.open_live_url(self.url)

        aidant: AidantRequest = self.request.aidant_requests.first()
        self._try_open_modal(By.ID, f"edit-button-{aidant.pk}")

        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-suppress"
        ).click()

        self.wait.until(self._modal_closed())

        self.assertElementNotFound(By.ID, f"profile-edit-card-{aidant.pk}")
        self.assertEqual(
            {self.request.aidant_requests.last()},
            set(self.request.aidant_requests.all()),
        )

    def test_modify_issuer(self):
        self.open_live_url(self.url)

        self.selenium.find_element(By.ID, "tests-issuer-edit-button").click()
        self.wait.until(
            self.path_matches(
                "habilitation_modify_issuer_on_organisation",
                kwargs={
                    "issuer_id": f"{self.request.issuer.issuer_id}",
                    "uuid": f"{self.request.uuid}",
                },
            )
        )
        self.check_accessibility(
            "habilitation_modify_issuer_on_organisation", strict=False
        )

        for _ in range(10):
            if (new_email := self.faker.email()) != self.request.issuer.email:
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
                    "issuer_id": f"{self.request.issuer.issuer_id}",
                    "uuid": f"{self.request.uuid}",
                },
            )
        )

        self.assertIn(
            new_email, self.selenium.find_element(By.ID, "test-issuer-infos").text
        )

    def _fill_form_with_correct_email_and_assert(
        self, request: AidantRequest, modal_opened=False
    ):
        new_email = self._get_new_valid_email(request)
        if not modal_opened:
            self._try_open_modal(By.ID, f"edit-button-{request.pk}")

        email_input = self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #id_email"
        )
        email_input.clear()
        email_input.send_keys(new_email)
        self.selenium.find_element(
            By.CSS_SELECTOR, "#main-modal #profile-edit-submit"
        ).click()
        self.wait.until(self._modal_closed())

        request.refresh_from_db()
        self.assertEqual(request.email, new_email)

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

    def _get_new_valid_email(self, request: AidantRequest):
        emails = request.organisation.aidant_requests.values_list("email", flat=True)
        for _ in range(10):
            new_email = self.faker.email()
            if new_email not in emails:
                return new_email

        self.fail("This shouldn't happen")


@tag("functional")
class ReadonlyRequestView(ValidationRequestFormViewTests):
    def setUp(self):
        self.request: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.CHANGES_REQUIRED, post__aidants_count=2
        )
        self.url = reverse(
            "habilitation_organisation_view",
            kwargs={
                "issuer_id": self.request.issuer.issuer_id,
                "uuid": self.request.uuid,
            },
        )

    def test_I_can_modify_aidant(self):
        super().test_I_can_modify_aidant()

    def test_handle_errors(self):
        super().test_handle_errors()

    def test_delete(self):
        super().test_delete()

    def test_modify_issuer(self):
        super().test_modify_issuer()
