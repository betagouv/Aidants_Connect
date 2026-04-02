"""
Accessibility tests for public pages.

All pages here are simple template renders: no login, no complex setup.
Each page is tested for axe-core accessibility, title, and skiplinks.
"""

from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)

# url_name: Django URL name (reverse). title: expected <title> (str).
STATIC_PAGES = [
    {"url_name": "home_page", "title": "Accueil - Aidants Connect"},
    {
        "url_name": "cgu",
        "title": "Aidants Connect - Conditions générales d'utilisation",
    },
    {"url_name": "statistiques", "title": "Statistiques - Aidants Connect"},
    {"url_name": "mentions_legales", "title": "Mentions légales - Aidants Connect"},
    {
        "url_name": "politique_confidentialite",
        "title": "Aidants Connect - Politique de confidentialité",
    },
    {"url_name": "budget", "title": "Budget - Aidants Connect"},
    {
        "url_name": "accessibilite",
        "title": "Aidants Connect - Déclaration dʼaccessibilité",
    },
    {
        "url_name": "sandbox_presentation",
        "title": "Présentation du site bac à sable - Aidants Connect",
    },
    {"url_name": "sitemap", "title": "Plan du site - Aidants Connect"},
    {
        "url_name": "thanks_asking_mobile",
        "title": "Référent - Numéro de mobile enregistré - Aidants Connect",
    },
    {"url_name": "ressources", "title": "Ressources - Aidants Connect"},
    {"url_name": "habilitation_faq_formation", "title": "Formation - Aidants Connect"},
    {
        "url_name": "habilitation_faq_habilitation",
        "title": "Habilitation - Aidants Connect",
    },
    {
        "url_name": "manager_first_connexion_email_sent",
        "title": "Aidants Connect - Email envoyé (connexion)",
    },
]


class PublicPagesAccessibilityTests(AccessibilityTestCase):
    """Accessibility tests for all public pages (template-only render)."""

    async def _navigate_to(self, config):
        url = reverse(config["url_name"])
        await self.page.goto(self.live_server_url + url)
        await self.page.wait_for_load_state("domcontentloaded")

    @async_test
    async def test_accessibility(self):
        for config in STATIC_PAGES:
            url_name = config["url_name"]
            with self.subTest(page=url_name):
                self.__class__.common_page = None
                await self._navigate_to(config)
                await self.check_accessibility(
                    page_name=url_name,
                    strict=True,
                )
        self.__class__.common_page = None

    @async_test
    async def test_title_is_correct(self):
        for config in STATIC_PAGES:
            if config["title"] is None:
                continue
            with self.subTest(page=config["url_name"]):
                self.__class__.common_page = None
                await self._navigate_to(config)
                await expect(self.page).to_have_title(config["title"])
        self.__class__.common_page = None

    @async_test
    async def test_skiplinks_are_valid(self):
        for config in STATIC_PAGES:
            with self.subTest(page=config["url_name"]):
                self.__class__.common_page = None
                await self._navigate_to(config)
                nav_skiplinks = self.page.get_by_role("navigation", name="Accès rapide")
                skip_links = await nav_skiplinks.get_by_role("link").all()
                for skip_link in skip_links:
                    await expect(skip_link).to_be_attached()
                    await skip_link.focus()
                    await expect(skip_link).to_be_visible()
        self.__class__.common_page = None
