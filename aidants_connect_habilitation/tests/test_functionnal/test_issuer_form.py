from typing import List, Optional
from unittest.mock import ANY, Mock, patch

from django.test import tag
from django.urls import reverse

from faker import Faker
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.constants import HabilitationFormStep
from aidants_connect_habilitation.models import Issuer
from aidants_connect_habilitation.tests.factories import IssuerFactory


@tag("functional")
class IssuerFormViewTests(FunctionalTestCase):
    def test_display_correct_railway(self):
        self.__open_form_url()

        issuer_station: WebElement = self.selenium.find_elements(
            By.XPATH, "//*[contains(@class, 'habilitation-breadcrumbs')]//li"
        )[HabilitationFormStep.ISSUER.value - 1]

        self.assertIn("active", issuer_station.get_attribute("class").split())

    def test_submit_form_without_phone_passes(self):
        email = Faker().email()
        issuer = IssuerFactory.build(email=email)

        self.__open_form_url()

        self.__fill_form_and_submit(
            issuer, ["first_name", "last_name", "email", "profession"]
        )

        path = reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": Issuer.objects.get(email=email).issuer_id},
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def test_submit_form_with_phone_passes(self):
        email = Faker().email()
        issuer = IssuerFactory.build(email=email)

        self.__open_form_url()

        self.__fill_form_and_submit(
            issuer, ["first_name", "last_name", "email", "profession", "phone"]
        )

        path = reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": Issuer.objects.get(email=email).issuer_id},
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    @patch("aidants_connect_habilitation.signals.send_mail")
    def test_email_confirmation_process(self, send_mail_mock: Mock):
        email = Faker().email()
        issuer = IssuerFactory.build(email=email)

        self.__open_form_url()

        self.__fill_form_and_submit(
            issuer, ["first_name", "last_name", "email", "profession", "phone"]
        )

        path = reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": Issuer.objects.get(email=email).issuer_id},
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        send_mail_mock.assert_called_with(
            from_email=ANY,
            recipient_list=[email],
            subject=ANY,
            message=ANY,
            html_message=ANY,
        )

        # Test resend mail
        send_mail_mock.reset_mock()
        send_mail_mock.assert_not_called()

        self.selenium.find_element(
            By.XPATH,
            """//button[normalize-space() = "Renvoyer l'email de confirmation"]""",
        ).click()

        send_mail_mock.assert_called_with(
            from_email=ANY,
            recipient_list=[email],
            subject=ANY,
            message=ANY,
            html_message=ANY,
        )

        # Confirm email
        issuer = Issuer.objects.get(email=email)
        email_confirmation = issuer.email_confirmations.first()

        self.open_live_url(
            reverse(
                "habilitation_issuer_email_confirmation_confirm",
                kwargs={"issuer_id": issuer.issuer_id, "key": email_confirmation.key},
            )
        )

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": issuer.issuer_id},
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def __fill_form_and_submit(self, issuer: Issuer, fields: List[str]):
        for field in fields:
            try:
                self.selenium.find_element(By.ID, f"id_{field}").send_keys(
                    str(getattr(issuer, field))
                )
            except Exception as e:
                raise ValueError(f"Error when setting input 'id_{field}'") from e

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

    def __open_form_url(self, issuer: Optional[Issuer] = None):
        pattern = "habilitation_modify_issuer" if issuer else "habilitation_new_issuer"
        kwargs = {"issuer_id": issuer.issuer_id} if issuer else {}
        self.open_live_url(reverse(pattern, kwargs=kwargs))
