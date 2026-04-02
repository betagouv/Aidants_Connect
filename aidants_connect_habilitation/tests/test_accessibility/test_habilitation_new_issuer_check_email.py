from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_habilitation.models import Issuer


class HabilitationNewIssuerCheckEmailAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        # Create issuer directly in database
        self.issuer = Issuer.objects.create(
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@yopmail.com",
            profession="Infirmier",
        )

    async def _open_url(self):
        # Navigate directly to email confirmation page
        url = reverse(
            "habilitation_issuer_email_confirmation_waiting",
            args=[str(self.issuer.issuer_id)],
        )
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(
            page_name="habilitation_issuer_email_confirmation_waiting", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title("Confirmez votre email - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
