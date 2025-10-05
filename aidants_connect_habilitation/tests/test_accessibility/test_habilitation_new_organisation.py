from playwright.async_api import expect

from aidants_connect_common.constants import RequestOriginConstants
from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_habilitation.tests.factories import (
    IssuerFactory,
    OrganisationRequestFactory,
)


class HabilitationNewOrganisationAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.issuer = IssuerFactory()
        self.request = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
            france_services_number=444888555,
        )

    async def _open_url(self):
        await self.page.goto(
            self.live_server_url
            + f"/habilitation/demandeur/{self.issuer.issuer_id}"
            + f"/organisation/nouvelle/{self.request.siret}/"
        )
        await self.page.wait_for_load_state("networkidle")

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(
            page_name="habilitation_new_organisation", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title("Structure - Aidants Connect")

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
