from django.test import tag
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
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

        self.aidant_with_multiple_orgs = AidantFactory(organisation=self.organisation)
        self.aidant_with_multiple_orgs.organisations.add(
            OrganisationFactory(),
            OrganisationFactory(),
        )

        self.aidant_with_one_org = AidantFactory(organisation=self.organisation)

    def __get_live_url(self, organisation_id: int):
        return reverse(
            "espace_responsable_organisation",
            kwargs={"organisation_id": organisation_id},
        )

    def test_grouped_autorisations(self):
        root_path = self.__get_live_url(self.organisation.id)

        self.open_live_url(root_path)

        # Login
        self.login_aidant(self.aidant_responsable)
        self.wait.until(url_matches(f"^.+{root_path}$"))

        # Check button text
        button = self.selenium.find_element(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.id}-from-organisation",
        )
        self.assertEqual(
            "Retirer l’aidant de l’organisation",
            button.text,
        )

        button = self.selenium.find_element(
            By.ID, f"remove-aidant-{self.aidant_with_one_org.id}-from-organisation"
        )
        self.assertEqual("Désactiver l’aidant", button.text)

        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(
                By.ID, f"remove-aidant-{self.aidant_responsable.id}-from-organisation"
            )

        # Let's try those btns shall we?
        button.click()
        path = reverse(
            "espace_responsable_remove_aidant_from_organisation",
            kwargs={
                "organisation_id": self.organisation.id,
                "aidant_id": self.aidant_with_one_org.id,
            },
        )
        self.wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Confirmer']"
        ).click()

        self.wait.until(url_matches(f"^.+{root_path}$"))

        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(
                By.ID, f"remove-aidant-{self.aidant_with_one_org.id}-from-organisation"
            )

        self.selenium.find_element(
            By.ID,
            f"remove-aidant-{self.aidant_with_multiple_orgs.id}-from-organisation",
        ).click()
        path = reverse(
            "espace_responsable_remove_aidant_from_organisation",
            kwargs={
                "organisation_id": self.organisation.id,
                "aidant_id": self.aidant_with_multiple_orgs.id,
            },
        )
        self.wait.until(url_matches(f"^.+{path}$"))

        self.selenium.find_element(
            By.XPATH, "//button[@type='submit' and normalize-space(text())='Confirmer']"
        ).click()

        self.wait.until(url_matches(f"^.+{root_path}$"))

        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(
                By.ID,
                f"remove-aidant-{self.aidant_with_multiple_orgs.id}-from-organisation",
            )

        pass
