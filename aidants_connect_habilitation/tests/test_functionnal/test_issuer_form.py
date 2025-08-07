from typing import List, Optional
from unittest.mock import ANY, Mock, patch

from django.test import tag
from django.urls import reverse

from faker import Faker
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.models import Issuer
from aidants_connect_habilitation.tests.factories import IssuerFactory


@tag("functional", "habilitation")
class IssuerFormViewTests(FunctionalTestCase):
    def test_submit_form_without_phone_passes(self):
        email = Faker().email()
        issuer = IssuerFactory.build(email=email)

        self.__open_form_url()
        self.check_accessibility("habilitation_new_issuer", strict=False)

        self.__fill_form_and_submit(
            issuer, ["first_name", "last_name", "email", "profession"]
        )

        path = reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": Issuer.objects.get(email=email).issuer_id},
        )
        self.check_accessibility(
            "habilitation_issuer_email_confirmation_waiting", strict=False
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

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

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
        self.check_accessibility(
            "habilitation_issuer_email_confirmation_confirm", strict=False
        )

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": issuer.issuer_id},
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))
        self.check_accessibility("habilitation_new_organisation", strict=False)

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
