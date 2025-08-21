import asyncio
import re
from urllib.parse import urlencode

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import tag
from django.urls import reverse

from playwright.async_api import async_playwright


def async_test(func):
    """Décorateur pour transformer une méthode async en test synchrone."""

    def wrapper(self):
        return self.loop.run_until_complete(func(self))

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


@tag("accessibility")
class AccessibilityTestCase(StaticLiveServerTestCase):
    """
    Classe de base pour les tests d'accessibilité avec Playwright.
    Utilise un décorateur @async_test pour une syntaxe élégante.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.loop.run_until_complete(cls._async_setup())

    @classmethod
    async def _async_setup(cls):
        cls.playwright = await async_playwright().start()
        cls.browser = await cls.playwright.chromium.launch(headless=False, slow_mo=1500)

    @classmethod
    def tearDownClass(cls):
        cls.loop.run_until_complete(cls._async_teardown())
        cls.loop.close()
        super().tearDownClass()

    @classmethod
    async def _async_teardown(cls):
        if cls.browser:
            await cls.browser.close()
        if cls.playwright:
            await cls.playwright.stop()

    def setUp(self):
        super().setUp()
        self.loop.run_until_complete(self._async_test_setup())

    async def _async_test_setup(self):
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    def tearDown(self):
        self.loop.run_until_complete(self._async_test_teardown())
        super().tearDown()

    async def _async_test_teardown(self):
        if hasattr(self, "context") and self.context:
            await self.context.close()

    def path_matches(
        self, viewname: str, *, kwargs: dict = None, query_params: dict = None
    ):
        kwargs = kwargs or {}
        query_part = urlencode(query_params or {}, quote_via=lambda s, _1, _2, _3: s)
        query_part = rf"\?{query_part}" if query_part else ""
        return rf"http://localhost:\d+{reverse(viewname, kwargs=kwargs)}{query_part}"

    async def wait_for_path_match(
        self, viewname: str, *, kwargs: dict = None, query_params: dict = None
    ):
        """Attendre qu'une URL corresponde au pattern de la vue Django"""
        pattern = self.path_matches(viewname, kwargs=kwargs, query_params=query_params)
        await self.page.wait_for_url(re.compile(pattern))

    async def login_aidant(self, aidant, otp_code: str):
        await self.page.goto(self.live_server_url + "/accounts/login/")
        await self.page.fill("#id_email", aidant.email)
        await self.page.fill("#id_otp_token", otp_code)
        await self.page.click("[type='submit']")

        await self.wait_for_path_match("magicauth-email-sent")

        url = (
            re.findall(r"https?://\S+", mail.outbox[-1].body, flags=re.M)[0]
            .replace("https", "http", 1)
            .replace("chargement/code", "code", 1)
        )
        await self.page.goto(url)
