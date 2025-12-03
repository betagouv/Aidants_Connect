import asyncio
import re
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import tag
from django.urls import reverse

from axe_playwright_python.async_playwright import Axe
from playwright.async_api import async_playwright


def async_test(func):
    """Décorateur pour transformer une méthode async en test synchrone."""

    def wrapper(self):
        return self.loop.run_until_complete(func(self))

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


@tag("functional")
class FunctionalTestCase(StaticLiveServerTestCase):
    """
    Classe de base pour les tests fonctionnales avec Playwright.
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
        cls.browser = await cls.playwright.chromium.launch(
            channel="chrome",
            headless=settings.HEADLESS_FUNCTIONAL_TESTS,
            slow_mo=100 if settings.HEADLESS_FUNCTIONAL_TESTS else 1500,
        )

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

    async def navigate_to_url(self, url_path: str):
        """
        Navigation standardisée vers une URL avec attente networkidle

        Args:
            url_path: Chemin relatif de l'URL (ex: "/", "/activity_check/")
        """
        await self.page.goto(self.live_server_url + url_path)
        await self.page.wait_for_load_state("domcontentloaded")

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
        await self.page.wait_for_load_state("domcontentloaded")


@tag("accessibility")
class AccessibilityTestCase(FunctionalTestCase):
    """
    Classe de base pour les tests d'accessibilité avec Playwright.
    Utilise un décorateur @async_test pour une syntaxe élégante.
    Inclut un système de lazy loading pour partager les pages entre tests.
    """

    common_page = None

    async def lazy_loading(self, navigation_method):
        """
        Lazy loading générique pour partager une page entre tests d'une même classe.

        Args:
            navigation_method: Méthode async qui navigue vers la page cible
        """
        if self.__class__.common_page is None:
            await navigation_method()
            self.__class__.common_page = self.page
        else:
            self.page = self.__class__.common_page

    def tearDown(self):
        """Override pour éviter de fermer la page partagée entre tests."""
        if hasattr(self, "page") and self.page is self.__class__.common_page:
            # Ne pas fermer la page si elle est partagée
            pass
        else:
            super().tearDown()

    @classmethod
    def tearDownClass(cls):
        """Override pour nettoyer la page partagée à la fin de tous les tests."""
        if hasattr(cls, "common_page") and cls.common_page is not None:
            if hasattr(cls.common_page, "context"):
                cls.loop.run_until_complete(cls.common_page.context.close())
        super().tearDownClass()

    async def check_accessibility(
        self,
        page_name="page",
        strict=False,
        options={
            "exclude": [
                ["nav[aria-label='Accès rapide']"],
                ["header[role='banner']"],
                ["nav[role='navigation']"],
                ["footer[role='contentinfo']"],
            ]
        },
    ):
        """
        Check accessibility of the current page using axe-core with Playwright

        Args:
            page_name: Name for the results file
            strict: If True, fail the test on violations
            options: Custom options for axe-core

        Returns:
            dict: axe-core results
        """
        if not hasattr(self, "axe") or self.axe is None:
            self.axe = Axe()

        try:
            results = await self.axe.run(self.page, options=options)
        except Exception:
            self.axe = Axe()
            results = await self.axe.run(self.page, options=options)

        violations_count = results.violations_count
        if violations_count > 0:
            violation_message = results.generate_report()

            if strict:
                self.assertEqual(violations_count, 0, violation_message)
            else:
                print(
                    f"\n{'=' * 100}\n",
                    f"\n⚠️  ACCESSIBILITY WARNING [{page_name}]:",
                    f"{violations_count} violation(s) detected",
                )
                print(f"{'=' * 100}\n")
                print(violation_message)

        return results
