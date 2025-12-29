from django.test import Client
from django.urls import reverse

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
            mandat_is_remote=True,
            remote_constent_method="SMS",
            user_phone="+33123456789",
            consent_request_id="test-consent-id-123",
        )

        # Configure session with connection data
        self._setup_session()

    def _setup_session(self):
        """Configure Django session with connection data"""
        client = Client()
        client.force_login(self.aidant)
        session = client.session
        session["connection"] = self.connection.id
        session.save()
        self.session_key = session.session_key

    async def _open_url(self):
        """Helper method to navigate to new_mandat_waiting_room page"""
        await self.login_aidant(self.aidant, self.otp_token)

        # Set session cookie
        await self.page.context.add_cookies(
            [
                {
                    "name": "sessionid",
                    "value": self.session_key,
                    "domain": "localhost",
                    "path": "/",
                }
            ]
        )

        # Navigate directly to waiting room
        url = reverse("new_mandat_waiting_room")
        await self.page.goto(self.live_server_url + url)

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
