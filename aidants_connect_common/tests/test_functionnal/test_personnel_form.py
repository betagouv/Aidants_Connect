import re

from django.core import mail
from django.test import tag
from django.urls import reverse

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    invisibility_of_element_located,
    visibility_of_element_located,
)

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.models import Issuer
from aidants_connect_habilitation.tests.factories import IssuerFactory


@tag("functional")
class FollowMyHabilitationRequestViewTests(FunctionalTestCase):
    def test_follow_my_request_modale(self):
        iss: Issuer = IssuerFactory()

        self.open_live_url(reverse("habilitation_faq_formation"))

        # Test bad email generating an error
        self._open_modale()
        self.selenium.find_element(By.ID, "id_email").send_keys("nope@test.test")
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.assertEqual(
            "Il nʼexiste pas de demande dʼhabilitation associée à cet email. "
            "Veuillez vérifier votre saisie ou renseigner une autre adresse email.",
            self.selenium.find_element(By.CSS_SELECTOR, ".errorlist").text.strip(),
        )

        self._close_modale()

        # Test correct email generating an error
        self._open_modale()
        self.selenium.find_element(By.ID, "id_email").send_keys(iss.email)
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.assertEqual(
            "Merci ! Nous venons de vous envoyer le lien vers votre demande "
            "dʼhabilitation à lʼadresse indiquée.",
            re.sub(
                r"\s+",
                " ",
                self.selenium.find_element(
                    By.CSS_SELECTOR, '[data-follow-request-modale-target="formContent"]'
                ).text,
            ).strip(),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [iss.email])

        self._close_modale()

        # Test a second time to verify that form is correctly reset
        self._open_modale()
        self.selenium.find_element(By.ID, "id_email").send_keys(iss.email)
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.assertEqual(
            "Merci ! Nous venons de vous envoyer le lien vers votre demande "
            "dʼhabilitation à lʼadresse indiquée.",
            re.sub(
                r"\s+",
                " ",
                self.selenium.find_element(
                    By.CSS_SELECTOR, '[data-follow-request-modale-target="formContent"]'
                ).text,
            ).strip(),
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, [iss.email])

    def _open_modale(self):
        def try_open_modal(driver):
            try:
                self.selenium.find_element(
                    By.ID, "follow-my-habilitation-request-btn"
                ).click()
            except NoSuchElementException:
                return False

            return visibility_of_element_located(
                (By.ID, "fr-modal-follow-hab-request-title")
            )(driver)

        self.wait.until(try_open_modal)

    def _close_modale(self):
        self.selenium.find_element(
            By.CSS_SELECTOR, '[data-controller="follow-request-modale"] .fr-btn--close'
        ).click()

        self.wait.until(
            invisibility_of_element_located((By.ID, "fr-modal-follow-hab-request"))
        )
