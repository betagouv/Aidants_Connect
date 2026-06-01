from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.tests.factories import AidantFactory


class NewMandatAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.aidant = AidantFactory(post__with_otp_device=True)
        # Récupérer le token de manière synchrone dans setUp
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

    async def _open_url(self):
        """Helper method to navigate to new_mandat page"""
        await self.login_aidant(self.aidant, self.otp_token)
        url = reverse("espace_aidant:new_mandat")
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(
            page_name="espace_aidant:new_mandat", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title("Nouveau mandat - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()

    @async_test
    async def test_required_fields_notice_is_present(self):
        await self.lazy_loading(self._open_url)
        page_content = await self.page.content()
        self.assertIn("sauf mention contraire", page_content.lower())
        self.assertIn("champs sont obligatoires", page_content.lower())

    @async_test
    async def test_mandat_form_steps(self):
        await self.lazy_loading(self._open_url)
        step_headings = self.page.locator("form h2.fr-label.title-count")
        await expect(step_headings).to_have_count(4)
        await expect(step_headings.nth(0)).to_have_text("Informez l’usager")
        await expect(step_headings.nth(1)).to_have_text(
            "Sélectionnez la ou les démarches"
        )
        await expect(step_headings.nth(2)).to_have_text("Choisissez la durée du mandat")
        await expect(step_headings.nth(3)).to_have_text(
            "Connectez l’usager à FranceConnect"
        )
        await expect(self.page.locator("#id_is_remote")).to_have_count(0)
