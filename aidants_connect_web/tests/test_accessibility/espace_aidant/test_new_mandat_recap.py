from django.conf import settings
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


class NewMandatRecapAccessibilityTests(AccessibilityTestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = settings.FC_AS_FS_TEST_PORT
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

        # Configurer la session de manière synchrone et propre
        self._setup_session()

    def _setup_session(self):
        """Configure la session Django avec l'ID de connection de manière synchrone"""
        # Utiliser le client de test Django pour créer une session propre
        client = Client()
        client.force_login(self.aidant)

        # Configurer la session avec l'ID de connection
        session = client.session
        session["connection"] = self.connection.id
        session.save()

        # Stocker la clé de session pour l'utiliser dans Playwright
        self.session_key = session.session_key

    async def _open_url(self):
        """Helper method to navigate to navigate_to_new_mandat_recap page"""
        await self.login_aidant(self.aidant, self.otp_token)

        # Injecter le cookie de session configuré dans setUp()
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

        # Naviguer vers la page de récapitulatif
        url = reverse("new_mandat_recap")
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(page_name="new_mandat_recap", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title(
            "Récapitulatif du nouveau mandat - Aidants Connect"
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

    @async_test
    async def test_required_fields_notice_is_present(self):
        await self.lazy_loading(self._open_url)
        page_content = await self.page.content()
        self.assertIn("sauf mention contraire", page_content.lower())
        self.assertIn("champs sont obligatoires", page_content.lower())
