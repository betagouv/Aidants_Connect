from django.core.management import call_command

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)


class TestimoniesAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        call_command("loaddata", "testimonies.json")

    @async_test
    async def test_testimonies_accessibility(self):
        await self.page.goto(self.live_server_url + "/temoignages/marie-dubois/")
        await self.page.wait_for_load_state("networkidle")
        await self.check_accessibility(
            page_name="testimonies_marie_dubois", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.page.goto(self.live_server_url + "/temoignages/marie-dubois/")
        await expect(self.page).to_have_title(
            "Témoignage Marie Dubois - Aidants Connect"
        )

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.page.goto(self.live_server_url + "/temoignages/marie-dubois/")

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()

            await skip_link.focus()
            await expect(skip_link).to_be_visible()
