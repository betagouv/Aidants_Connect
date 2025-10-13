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

    async def _open_url(self):
        await self.page.goto(self.live_server_url + "/temoignages/marie-dubois/")
        await self.page.wait_for_load_state("networkidle")

    @async_test
    async def test_testimonies_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(
            page_name="testimonies_marie_dubois", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title(
            "Témoignage Marie Dubois - Aidants Connect"
        )

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()

            await skip_link.focus()
            await expect(skip_link).to_be_visible()


class HelpAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        call_command("loaddata", "faq.json")

    async def _open_url(self):
        await self.page.goto(self.live_server_url + "/faq/")
        await self.page.wait_for_load_state("networkidle")

    @async_test
    async def test_help_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(page_name="faq_generale", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title(
            "FAQ Questions générales - Aidants Connect"
        )

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()

            await skip_link.focus()
            await expect(skip_link).to_be_visible()
