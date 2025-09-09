from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.tests.factories import AidantFactory, MandatFactory


class EndUserDetailsAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.aidant_thierry = AidantFactory(email="thierry@thierry.com")
        device = self.aidant_thierry.staticdevice_set.create(id=self.aidant_thierry.id)
        device.token_set.create(token="123456")

        self.mandat = MandatFactory(
            organisation=self.aidant_thierry.organisation,
            post__create_authorisations=["argent", "famille"],
        )

    @async_test
    async def test_accessibility(self):
        await self.login_aidant(self.aidant_thierry, "123456")
        await self.page.goto(
            self.live_server_url + f"/usagers/{self.mandat.usager.id}/"
        )
        await self.page.wait_for_load_state("networkidle")
        await self.check_accessibility(page_name="usager_details", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.login_aidant(self.aidant_thierry, "123456")
        await self.page.goto(
            self.live_server_url + f"/usagers/{self.mandat.usager.id}/"
        )
        await expect(self.page).to_have_title("Homer Simpson - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.login_aidant(self.aidant_thierry, "123456")
        await self.page.goto(
            self.live_server_url + f"/usagers/{self.mandat.usager.id}/"
        )
        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
