from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, CarteTOTPFactory


class EspaceResponsableFicheAidantAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.responsable_tom = AidantFactory(
            username="tom@tom.fr",
            post__with_otp_device=True,
        )
        self.responsable_tom.responsable_de.add(self.responsable_tom.organisation)
        self.otp_token = (
            self.responsable_tom.staticdevice_set.first().token_set.first().token
        )
        self.aidant_tim: Aidant = AidantFactory(
            username="tim@tim.fr",
            organisation=self.responsable_tom.organisation,
            first_name="Tim",
            last_name="Onier",
        )
        self.aidant_sarah: Aidant = AidantFactory(
            username="sarah@sarah.fr",
            organisation=self.responsable_tom.organisation,
            first_name="Sarah",
            last_name="Onier",
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=True,
        )
        self.deactivated_aidant: Aidant = AidantFactory(
            username="deactivated@deactivated.fr",
            organisation=self.responsable_tom.organisation,
            first_name="Deactivated",
            last_name="Onier",
            is_active=False,
        )
        self.carte = CarteTOTPFactory(seed="zzzz")
        self.org_id = self.responsable_tom.organisation.id

    async def _open_url(self):
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url + f"/espace-responsable/aidant/{self.aidant_sarah.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_sarah.id},
        )

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility("espace_responsable_aidant", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        full_name = self.aidant_sarah.get_full_name()
        await expect(self.page).to_have_title(f"{full_name} - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)
        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
