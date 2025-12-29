from datetime import timedelta

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.models import Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AutorisationFactory,
    ConnectionFactory,
    MandatFactory,
    UsagerFactory,
)

FC_URL_PARAMETERS = (
    f"state=34"
    f"&nonce=45"
    f"&response_type=code"
    f"&client_id={settings.FC_AS_FI_ID}"
    f"&redirect_uri={settings.FC_AS_FI_CALLBACK_URL}"
    f"&scope=openid profile email address phone birth"
    f"&acr_values=eidas1"
)


class SelectDemarcheAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.aidant_1 = AidantFactory()
        device = self.aidant_1.staticdevice_set.create(id=self.aidant_1.id)
        device.token_set.create(token="123456")
        self.aidant_2 = AidantFactory()
        self.usager_josephine = UsagerFactory(
            given_name="Joséphine", family_name="ST-PIERRE"
        )
        self.usager_anne = UsagerFactory(
            given_name="Anne Cécile Gertrude", family_name="EVALOUS"
        )

        mandat_aidant_1_jo_6 = MandatFactory(
            organisation=self.aidant_1.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=mandat_aidant_1_jo_6,
            demarche="argent",
        )

        mandat_aidant_1_jo_12 = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )

        AutorisationFactory(
            mandat=mandat_aidant_1_jo_12,
            demarche="famille",
        )

        mandat_aidant_2_jo_12 = Mandat.objects.create(
            organisation=self.aidant_2.organisation,
            usager=self.usager_josephine,
            expiration_date=timezone.now() + timedelta(days=12),
        )
        AutorisationFactory(
            mandat=mandat_aidant_2_jo_12,
            demarche="logement",
        )

        # Configure session with Connection data
        self._setup_session()

    def _setup_session(self):
        """Configure Django session with Connection"""
        # Create a complete Connection as required by FISelectDemarche
        self.connection = ConnectionFactory(
            usager=self.usager_josephine,
            state="34",
            nonce="45",
            complete=False,  # Not yet completed
            aidant=self.aidant_1,
            organisation=self.aidant_1.organisation,
        )

        client = Client()
        client.force_login(self.aidant_1)
        session = client.session
        session["connection"] = self.connection.pk
        session.save()
        self.session_key = session.session_key

    async def _open_url(self):
        await self.login_aidant(self.aidant_1, "123456")

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

        # Navigate directly to select_demarche
        url = reverse("fi_select_demarche")
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(page_name="select_demarche", strict=True)

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title(
            "Sélection de la démarche - Aidants Connect"
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
