from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)


class LoginPageAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.login_paths = [
            "/accounts/login/",
            "/accounts/manager_first_login/",
        ]

    @async_test
    async def test_title_is_correct(self):
        for path in self.login_paths:
            await self.navigate_to_url(path)
            await expect(self.page).to_have_title("Connectez-vous - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        for path in self.login_paths:
            await self.navigate_to_url(path)

            nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
            skip_links = await nav_skiplinks.get_by_role("link").all()

            for skip_link in skip_links:
                await expect(skip_link).to_be_attached()
                await skip_link.focus()
                await expect(skip_link).to_be_visible()

    @async_test
    async def test_required_fields_notice_is_present(self):
        for path in self.login_paths:
            await self.navigate_to_url(path)

            page_content = await self.page.content()
            self.assertIn("sauf mention contraire", page_content.lower())
            self.assertIn("champs sont obligatoires", page_content.lower())
