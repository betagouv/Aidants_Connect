from typing import Optional

from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_habilitation.models import Issuer


class IssuerFormViewTests(AccessibilityTestCase):
    async def open_form_url(self, issuer: Optional[Issuer] = None):
        pattern = "habilitation_modify_issuer" if issuer else "habilitation_new_issuer"
        kwargs = {"issuer_id": issuer.issuer_id} if issuer else {}
        url = reverse(pattern, kwargs=kwargs)
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_title_is_correct(self):
        await self.open_form_url()
        await expect(self.page).to_have_title("Nouveau demandeur - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.open_form_url()

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
