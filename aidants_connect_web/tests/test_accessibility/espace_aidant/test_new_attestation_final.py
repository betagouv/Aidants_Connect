from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.models import Aidant, Mandat
from aidants_connect_web.tests.factories import AidantFactory, MandatFactory


class NewAttestationFinalAccessibilityTests(AccessibilityTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_1: Aidant = AidantFactory()
        cls.mandat: Mandat = MandatFactory(
            post__create_authorisations=["argent", "papiers"],
            organisation=cls.aidant_1.organisation,
        )

    def setUp(self):
        super().setUp()
        self.otp = "123455"
        self.aidant: Aidant = AidantFactory(post__with_otp_device=["123456", self.otp])
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token
        self.mandat: Mandat = MandatFactory(
            post__create_authorisations=["argent", "papiers"],
            organisation=self.aidant.organisation,
        )

    async def _open_url(self):
        """Helper method to navigate to navigate_to_new_attestation_final page"""
        await self.login_aidant(self.aidant, self.otp)
        url = reverse("new_attestation_final", args=(self.mandat.pk,))
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(page_name="new_attestation_final", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title("Impression du mandat - Aidants Connect")

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
