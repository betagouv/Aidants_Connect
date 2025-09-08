from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


class EspaceResponsableFicheAidantAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        organisation = OrganisationFactory()
        self.aidant_responsable: Aidant = AidantFactory(
            organisation=organisation,
            post__with_otp_device=True,
            post__is_organisation_manager=True,
        )
        self.otp_token = (
            self.aidant_responsable.staticdevice_set.first().token_set.first().token
        )

    async def navigate_to_helper_page(self):
        await self.login_aidant(self.aidant_responsable, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_responsable.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_responsable.id},
        )

    @async_test
    async def test_accessibility(self):
        await self.navigate_to_helper_page()
        await self.check_accessibility("espace_responsable_aidant", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.navigate_to_helper_page()
        full_name = self.aidant_responsable.get_full_name()
        await expect(self.page).to_have_title(f"{full_name} - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.navigate_to_helper_page()
        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
