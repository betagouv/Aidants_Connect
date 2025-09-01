from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.tests.factories import AidantFactory


class ActivityCheckAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.aidant = AidantFactory(post__with_otp_device=True)
        # Récupérer le token de manière synchrone dans setUp
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

    async def navigate_to_page(self):
        """Helper method to navigate to new_mandat page"""
        await self.login_aidant(self.aidant, self.otp_token)
        await self.page.goto(self.live_server_url + "/activity_check/")

    @async_test
    async def test_title_is_correct(self):
        await self.navigate_to_page()
        await expect(self.page).to_have_title("Session expirée - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.navigate_to_page()

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()

            await skip_link.focus()
            await expect(skip_link).to_be_visible()

    @async_test
    async def test_required_fields_notice_is_present(self):
        await self.navigate_to_page()

        page_content = await self.page.content()
        self.assertIn("sauf mention contraire", page_content.lower())
        self.assertIn("champs sont obligatoires", page_content.lower())
