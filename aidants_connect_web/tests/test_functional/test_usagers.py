from datetime import timedelta

from django.utils import timezone

from selenium.webdriver.common.by import By

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ExpiredMandatFactory,
    MandatFactory,
    RevokedMandatFactory,
    UsagerFactory,
)


class UsagersTest(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory(
            email="thierry@thierry.com", post__with_otp_device=True
        )

        self.usager_josephine = UsagerFactory(
            given_name="Joséphine", family_name="ST-PIERRE"
        )

        self.usager_anne = UsagerFactory(
            given_name="Anne Cécile Gertrude", family_name="EVALOUS"
        )

        self.usager_corentin = UsagerFactory(
            given_name="Corentin", family_name="Dupont", preferred_username="Anne"
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_josephine,
            post__create_authorisations=["argent", "famille"],
        )

        ExpiredMandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_corentin,
            post__create_authorisations=["argent", "famille", "logement"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager_anne,
            post__create_authorisations=["argent", "famille", "logement"],
        )

    def test_tabs_navigation(self):
        self.open_live_url("/usagers/")
        self.login_aidant(self.aidant)

        self.wait.until(self.document_loaded())

        user_with_valid_mandate = self.selenium.find_elements(
            By.CSS_SELECTOR, "table.with-valid-mandate tbody tr"
        )

        user_without_valid_mandate = self.selenium.find_elements(
            By.CSS_SELECTOR, "table.without-valid-mandate tbody tr"
        )

        self.assertEqual(len(user_with_valid_mandate), 2)
        self.assertEqual(len(user_without_valid_mandate), 1)

        active_tab = self.selenium.find_element(By.ID, "tab-1")
        self.assertEqual(active_tab.get_attribute("aria-selected"), "true")

        active_panel = self.selenium.find_element(By.ID, "tab-1-panel")
        self.assertIn("fr-tabs__panel--selected", active_panel.get_attribute("class"))

        expired_tab = self.selenium.find_element(By.ID, "tab-2")
        self.assertEqual(expired_tab.get_attribute("aria-selected"), "false")

        revoked_tab = self.selenium.find_element(By.ID, "tab-3")
        self.assertEqual(revoked_tab.get_attribute("aria-selected"), "false")

        expired_panel = self.selenium.find_element(By.ID, "tab-2-panel")
        self.assertIsNotNone(expired_panel)

        revoked_panel = self.selenium.find_element(By.ID, "tab-3-panel")
        self.assertIsNotNone(revoked_panel)

    def test_mandats_display_in_tabs(self):
        """Test display of mandats with different scopes in appropriate tabs"""
        usager_marie = UsagerFactory(given_name="Marie", family_name="MARTIN")
        usager_paul = UsagerFactory(given_name="Paul", family_name="BERNARD")
        usager_sophie = UsagerFactory(given_name="Sophie", family_name="DUBOIS")

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_marie,
            post__create_authorisations=["argent"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_paul,
            post__create_authorisations=[
                "papiers",
                "famille",
                "logement",
                "social",
            ],
        )

        ExpiredMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_marie,
            post__create_authorisations=["papiers", "social"],
        )

        RevokedMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_sophie,
            post__create_authorisations=["famille"],
        )

        RevokedMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_paul,
            post__create_authorisations=[
                "argent",
                "papiers",
                "famille",
            ],
        )

        self.open_live_url("/usagers/")
        self.login_aidant(self.aidant)

        self.wait.until(self.document_loaded())

        active_panel = self.selenium.find_element(By.ID, "tab-1-panel")
        active_rows = active_panel.find_elements(By.CSS_SELECTOR, "table tbody tr")
        self.assertEqual(len(active_rows), 4)

        active_text = active_panel.text
        self.assertIn("Joséphine", active_text)
        self.assertIn("Anne Cécile Gertrude", active_text)
        self.assertIn("Marie", active_text)
        self.assertIn("Paul", active_text)

        expired_panel = self.selenium.find_element(By.ID, "tab-2-panel")
        expired_rows = expired_panel.find_elements(By.CSS_SELECTOR, "table tbody tr")
        self.assertEqual(len(expired_rows), 2)

        expired_html = expired_panel.get_attribute("innerHTML")
        self.assertIn("Corentin", expired_html)
        self.assertIn("Marie", expired_html)

        revoked_panel = self.selenium.find_element(By.ID, "tab-3-panel")
        revoked_rows = revoked_panel.find_elements(By.CSS_SELECTOR, "table tbody tr")
        self.assertEqual(len(revoked_rows), 2)

        revoked_html = revoked_panel.get_attribute("innerHTML")
        self.assertIn("Sophie", revoked_html)
        self.assertIn("Paul", revoked_html)

    def test_multiple_mandats_display(self):
        """Test display of users with multiple mandats"""

        usager_multiple = UsagerFactory(given_name="Jean", family_name="DUPONT")

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_multiple,
            creation_date=timezone.now() - timedelta(days=30),
            post__create_authorisations=["argent"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_multiple,
            creation_date=timezone.now() - timedelta(days=15),
            post__create_authorisations=["papiers", "famille"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_multiple,
            creation_date=timezone.now() - timedelta(days=5),
            post__create_authorisations=["logement", "social", "transport"],
        )

        usager_expired_multiple = UsagerFactory(
            given_name="Pierre", family_name="MARTIN"
        )

        ExpiredMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_expired_multiple,
            creation_date=timezone.now() - timedelta(days=60),
            post__create_authorisations=["argent"],
        )

        ExpiredMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_expired_multiple,
            creation_date=timezone.now() - timedelta(days=45),
            post__create_authorisations=["papiers", "famille"],
        )

        usager_revoked_multiple = UsagerFactory(
            given_name="Marie", family_name="BERNARD"
        )

        RevokedMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_revoked_multiple,
            creation_date=timezone.now() - timedelta(days=90),
            post__create_authorisations=["social"],
        )

        RevokedMandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_revoked_multiple,
            creation_date=timezone.now() - timedelta(days=75),
            post__create_authorisations=["logement", "transport"],
        )

        self.open_live_url("/usagers/")
        self.login_aidant(self.aidant)

        self.wait.until(self.document_loaded())

        active_panel = self.selenium.find_element(By.ID, "tab-1-panel")
        active_rows = active_panel.find_elements(By.CSS_SELECTOR, "table tbody tr")

        self.assertEqual(len(active_rows), 3)

        active_text = active_panel.text
        self.assertIn("Jean", active_text)
        self.assertIn("DUPONT", active_text)

        date_lists = active_panel.find_elements(By.CSS_SELECTOR, "ul li")
        self.assertGreaterEqual(len(date_lists), 3)

        auth_badges = active_panel.find_elements(By.CSS_SELECTOR, ".fr-tag")
        self.assertGreater(len(auth_badges), 0)

        expired_panel = self.selenium.find_element(By.ID, "tab-2-panel")
        expired_html = expired_panel.get_attribute("innerHTML")
        self.assertIn("Pierre", expired_html)
        self.assertIn("MARTIN", expired_html)

        expired_date_lists = expired_panel.find_elements(By.CSS_SELECTOR, "ul li")
        self.assertGreaterEqual(len(expired_date_lists), 2)

        revoked_panel = self.selenium.find_element(By.ID, "tab-3-panel")
        revoked_html = revoked_panel.get_attribute("innerHTML")
        self.assertIn("Marie", revoked_html)
        self.assertIn("BERNARD", revoked_html)

        revoked_date_lists = revoked_panel.find_elements(By.CSS_SELECTOR, "ul li")
        self.assertGreaterEqual(len(revoked_date_lists), 2)

    def test_duplicate_permissions_are_removed(self):
        usager_duplicates = UsagerFactory(given_name="Lucie", family_name="MARTIN")

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_duplicates,
            creation_date=timezone.now() - timedelta(days=30),
            post__create_authorisations=["argent", "famille"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_duplicates,
            creation_date=timezone.now() - timedelta(days=15),
            post__create_authorisations=["famille", "papiers"],
        )

        MandatFactory(
            organisation=self.aidant.organisation,
            usager=usager_duplicates,
            creation_date=timezone.now() - timedelta(days=5),
            post__create_authorisations=["argent", "logement"],
        )

        self.open_live_url("/usagers/")
        self.login_aidant(self.aidant)

        active_panel = self.selenium.find_element(By.ID, "tab-1-panel")

        rows = active_panel.find_elements(By.CSS_SELECTOR, "table tbody tr")
        lucie_row = None
        for row in rows:
            if "Lucie" in row.text and "MARTIN" in row.text:
                lucie_row = row
                break

        self.assertIsNotNone(lucie_row, "Could not find row for Lucie MARTIN")

        permission_tags = lucie_row.find_elements(By.CSS_SELECTOR, ".fr-tag")

        permission_texts = [tag.text.strip() for tag in permission_tags]

        expected_permissions = {"Argent", "Famille", "Papiers", "Logement"}
        actual_permissions = set(permission_texts)

        self.assertEqual(
            actual_permissions,
            expected_permissions,
            f"Expected {expected_permissions}, but got {actual_permissions}",
        )

        self.assertEqual(
            len(permission_tags),
            len(expected_permissions),
            f"Found {len(permission_tags)} tags, expected {len(expected_permissions)}",
        )
