from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


@tag("functional")
class RemoveAidantFromOrganisationTests(FunctionalTestCase):
    def setUp(self):
        self.organisation = OrganisationFactory()
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )

        self.aidant_disabled_with_card: Aidant = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
        )
        self.aidant_disabled_with_card.remove_from_organisation(self.organisation)

        self.aidant_with_card = AidantFactory(
            organisation=self.organisation,
            post__with_carte_totp=True,
        )

    def __get_live_url(self, organisation_id: int):
        return reverse(
            "espace_responsable_organisation",
            kwargs={"organisation_id": organisation_id},
        )

    def test_remove_card_from_aidant(self):
        root_path = self.__get_live_url(self.organisation.id)

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # First aidant: disabled
        self.assertIsNotNone(self.aidant_disabled_with_card.carte_totp)
        button1 = self.selenium.find_element(
            By.ID,
            f"remove-totp-card-from-aidant-{ self.aidant_disabled_with_card.id }",
        )
        self.assertEqual("Délier la carte", button1.text)

        button1.click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_aidant_remove_card",
                kwargs={"aidant_id": self.aidant_disabled_with_card.id},
            )
        )

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Dissocier']"
        ).click()

        self.wait.until(
            self.path_matches(
                "espace_responsable_organisation",
                kwargs={"organisation_id": self.aidant_responsable.organisation.pk},
            )
        )

        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_disabled_with_card.id}"
        )

        self.aidant_disabled_with_card.refresh_from_db()
        with self.assertRaises(Aidant.carte_totp.RelatedObjectDoesNotExist):
            self.aidant_disabled_with_card.carte_totp

        self.assertIsNotNone(self.aidant_with_card.carte_totp)
        button2 = self.selenium.find_element(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_with_card.id}"
        )
        self.assertEqual("Délier la carte", button2.text)

        # First aidant: active
        button2.click()
        self.wait.until(
            self.path_matches(
                "espace_responsable_aidant_remove_card",
                kwargs={"aidant_id": self.aidant_with_card.id},
            )
        )

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Dissocier']"
        ).click()

        self.wait.until(
            self.path_matches(
                "espace_responsable_organisation",
                kwargs={"organisation_id": self.aidant_responsable.organisation.pk},
            )
        )

        self.assertElementNotFound(
            By.ID, f"remove-totp-card-from-aidant-{self.aidant_with_card.id}"
        )

        self.aidant_with_card.refresh_from_db()
        with self.assertRaises(Aidant.carte_totp.RelatedObjectDoesNotExist):
            self.aidant_with_card.carte_totp
