from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)


class LoginPageAccessibilityTests(AccessibilityTestCase):
    @async_test
    async def test_title_is_correct(self):
        await self.page.goto(self.live_server_url + "/accounts/login/")
        await expect(self.page).to_have_title("Connectez-vous - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.page.goto(self.live_server_url + "/accounts/login/")

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
