import re

from django.conf import settings

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ConnectionFactory,
    UsagerFactory,
)


class NewAttestationFinalAccessibilityTests(AccessibilityTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.port = settings.FC_AS_FS_TEST_PORT
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.otp = "123455"
        self.aidant: Aidant = AidantFactory(post__with_otp_device=["123456", self.otp])
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

        self.usager = UsagerFactory()
        self.connection = ConnectionFactory(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            usager=self.usager,
            demarches=["papiers", "logement"],
            duree_keyword="SHORT",
        )

    async def _open_url(self):
        """Helper method to navigate to navigate_to_new_attestation_final page"""
        await self.login_aidant(self.aidant, self.otp)
        await self.navigate_to_url("/usagers/")
        await self.page.click("#add_usager")
        await self.wait_for_path_match("new_mandat")

        # fill-in new_mandate form
        await self.page.click("#id_demarche_argent ~ label")
        await self.page.click("#id_demarche_famille ~ label")
        await self.page.click("#id_duree_short ~ label")

        # FranceConnect
        await self.page.click(".fr-connect")
        await self.page.wait_for_url(
            re.compile(r"https://.+franceconnect\.fr/api/v1/authorize.+")
        )
        await self.page.click("#fi-identity-provider-example")
        await self.page.wait_for_url(
            re.compile(r"https://.+franceconnect\.fr/interaction/.+")
        )
        await self.page.locator('input[type="submit"]').first.click()
        await self.page.wait_for_url(
            re.compile(r"https://.+franceconnect\.fr/api/v1/authorize.+")
        )
        await self.page.click("button")
        await self.wait_for_path_match("logout_callback")

        # complete form
        await self.page.click("#id_personal_data ~ label")
        await self.page.fill("#id_otp_token", self.otp_token)
        await self.page.click('input[type="submit"]')

        # navigate to new_attestation_final
        await self.page.wait_for_url(
            re.compile(r".*/creation_mandat/visualisation/final/\d+")
        )
        await self.page.wait_for_load_state("networkidle")

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(page_name="new_attestation_final", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title("Impression du mandat - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
