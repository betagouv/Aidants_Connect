from datetime import timedelta

from django.utils import timezone

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)


class RenewMandatAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.otp = "123455"
        self.aidant: Aidant = AidantFactory(post__with_otp_device=["123456", self.otp])
        self.usager = UsagerFactory(given_name="Fabrice")
        self.token = self.aidant.staticdevice_set.first().token_set.first().token
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )

    async def navigate_to_renew_mandat(self):
        await self.login_aidant(self.aidant, self.token)
        await self.navigate_to_url(f"/renew_mandat/{self.usager.pk}")

    @async_test
    async def test_accessibility(self):
        await self.navigate_to_renew_mandat()
        await self.check_accessibility(page_name="new_mandat", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.navigate_to_renew_mandat()
        await expect(self.page).to_have_title("Renouveler un mandat - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.navigate_to_renew_mandat()

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()

    @async_test
    async def test_required_fields_notice_is_present(self):
        await self.navigate_to_renew_mandat()

        page_content = await self.page.content()
        self.assertIn("sauf mention contraire", page_content.lower())
        self.assertIn("champs sont obligatoires", page_content.lower())
