import re

from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_habilitation.tests.factories import (
    DraftOrganisationRequestFactory,
    IssuerFactory,
    ManagerFactory,
)


class HabilitationNewManagerAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.issuer = IssuerFactory()
        self.manager = ManagerFactory(is_aidant=False, conseiller_numerique=False)

        self.organisation = DraftOrganisationRequestFactory(
            issuer=self.issuer, manager=self.manager
        )

    async def _open_url(self):
        url = reverse(
            "habilitation_new_referent",
            args=[str(self.issuer.issuer_id), str(self.organisation.uuid)],
        )
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(
            page_name="habilitation_new_referent", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title(re.compile(r".*- Aidants Connect$"))

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
