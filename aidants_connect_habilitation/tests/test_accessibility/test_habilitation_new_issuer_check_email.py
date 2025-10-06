from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_habilitation.models import Issuer


class HabilitationNewIssuerCheckEmailAccessibilityTests(AccessibilityTestCase):
    async def navigate_to_url(self):
        await self.page.goto(self.live_server_url + "/habilitation/demandeur")
        issuer = Issuer(
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@yopmail.com",
            profession="Infirmier",
        )
        fields = ["first_name", "last_name", "email", "profession"]
        for field in fields:
            try:
                await self.page.fill(f"#id_{field}", str(getattr(issuer, field)))
            except Exception as e:
                raise ValueError(f"Error when setting input 'id_{field}'") from e

        await self.page.click('[type="submit"]')
        await self.page.wait_for_load_state("domcontentloaded")

    @async_test
    async def test_accessibility(self):
        await self.navigate_to_url()
        await self.check_accessibility(
            page_name="habilitation_issuer_email_confirmation_waiting", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.navigate_to_url()
        await expect(self.page).to_have_title("Confirmez votre email - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.navigate_to_url()

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
