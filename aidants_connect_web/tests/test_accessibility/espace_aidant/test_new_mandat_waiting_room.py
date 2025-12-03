from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ConnectionFactory,
    UsagerFactory,
)


class NewMandatWaitingRoomAccessibilityTests(AccessibilityTestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 0
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.aidant = AidantFactory(post__with_otp_device=True)
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

        self.usager = UsagerFactory()
        self.connection = ConnectionFactory(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            usager=self.usager,
            demarches=["papiers", "logement"],
            duree_keyword="SHORT",
        )

    async def _open_url(self):
        """Helper method to navigate to new_mandat_waiting_room page"""
        await self.login_aidant(self.aidant, self.otp_token)
        await self.navigate_to_url("/usagers/")
        await self.page.click("#add_usager")
        await self.wait_for_path_match("new_mandat")

        # fill-in new_mandate form
        await self.page.click("#id_demarche_argent ~ label")
        await self.page.click("#id_demarche_famille ~ label")
        await self.page.click("#id_duree_short ~ label")

        # Select remote method
        await self.page.click("#id_is_remote ~ label")
        # Wait for remote consent method fields to become required
        await self.page.wait_for_selector("#id_remote_constent_method_sms[required]")
        # Select SMS consent method
        await self.page.click("#id_remote_constent_method_sms ~ label")
        # Wait for phone fields to become required
        await self.page.wait_for_selector("#id_user_phone[required]")
        await self.page.wait_for_selector("#id_user_remote_contact_verified[required]")

        # fill phone number and verify contact
        await self.page.fill("#id_user_phone", "0 800 840 800")
        await self.page.click("#id_user_remote_contact_verified ~ label")

        # send recap mandate and go to second step
        await self.page.click(".fr-connect")
        await self.wait_for_path_match("new_mandat_remote_second_step")

        # send user consent request to reach waiting room
        await self.page.click('[type="submit"]')
        await self.wait_for_path_match("new_mandat_waiting_room")
        await self.page.wait_for_load_state("networkidle")

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(page_name="new_mandat_waiting_room", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title(
            "En attente de consentement - Aidants Connect"
        )

    @async_test
    async def test_skiplinks_are_valid(self):
        await self.lazy_loading(self._open_url)

        nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
        skip_links = await nav_skiplinks.get_by_role("link").all()

        for skip_link in skip_links:
            await expect(skip_link).to_be_attached()
            await skip_link.focus()
            await expect(skip_link).to_be_visible()
