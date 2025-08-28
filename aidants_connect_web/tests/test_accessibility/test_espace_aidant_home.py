from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.tests.factories import AidantFactory


class EspaceAidantHomeAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.aidant = AidantFactory(post__with_otp_device=True)
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

    @async_test
    async def test_title_is_correct(self):
        await self.login_aidant(self.aidant, self.otp_token)
        await expect(self.page).to_have_title("Espace Aidant - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.login_aidant(self.aidant, self.otp_token)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
