from django.urls import reverse

from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    AccessibilityTestCase,
    async_test,
)
from aidants_connect_web.tests.factories import AidantFactory


class NewMandatAccessibilityTests(AccessibilityTestCase):
    def setUp(self):
        super().setUp()
        self.aidant = AidantFactory(post__with_otp_device=True)
        # Récupérer le token de manière synchrone dans setUp
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

    async def _open_url(self):
        """Helper method to navigate to new_mandat page"""
        await self.login_aidant(self.aidant, self.otp_token)
        url = reverse("espace_aidant:new_mandat")
        await self.page.goto(self.live_server_url + url)

    @async_test
    async def test_accessibility(self):
        await self.lazy_loading(self._open_url)
        await self.check_accessibility(
            page_name="espace_aidant:new_mandat", strict=True
        )

    @async_test
    async def test_title_is_correct(self):
        await self.lazy_loading(self._open_url)
        await expect(self.page).to_have_title("Nouveau mandat - Aidants Connect")

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

    @async_test
    async def test_mandat_form_steps(self):
        await self.lazy_loading(self._open_url)
        steps = self.page.locator("form ol.mandat-steps > li.mandat-step")
        await expect(steps).to_have_count(4)
        step_headings = steps.locator("h2.fr-label.title-count")
        await expect(step_headings).to_have_count(4)
        await expect(step_headings.nth(0)).to_have_text("Lisez ces mentions à l’usager")
        await expect(step_headings.nth(1)).to_have_text(
            "Sélectionnez la ou les démarches"
        )
        await expect(step_headings.nth(2)).to_have_text("Choisissez la durée du mandat")
        await expect(step_headings.nth(3)).to_have_text(
            "Connectez l’usager à FranceConnect"
        )
        await expect(self.page.locator("#id_is_remote")).to_have_count(0)

    @async_test
    async def test_demarche_fieldset_has_required_hint(self):
        await self.lazy_loading(self._open_url)
        demarche_fieldset = self.page.locator("#demarche-fieldset")
        await expect(demarche_fieldset).to_be_attached()
        await expect(demarche_fieldset).to_have_attribute(
            "aria-describedby", "demarche-hint"
        )
        await expect(self.page.locator("#demarche-hint")).to_have_text(
            "Sélectionnez au moins une démarche."
        )
        legend = demarche_fieldset.locator("legend")
        await expect(legend).to_contain_text("Sélectionnez au moins une démarche.")

    @async_test
    async def test_demarche_error_summary_focus_and_link(self):
        # Do not use lazy_loading: this test POSTs the form. Shared pages keep a
        # stale session cookie after TransactionTestCase flushes the DB between
        # tests, so a POST would redirect to login and poison common_page.
        await self._open_url()
        await expect(self.page).to_have_title("Nouveau mandat - Aidants Connect")

        # Select a duration so HTML5 required validation on radios does not
        # block the POST; leave demarches empty to trigger the server error.
        await self.page.locator("form").evaluate("form => { form.noValidate = true; }")
        await self.page.locator("label[for='id_duree_short']").click()
        await expect(self.page.locator("#id_duree_short")).to_be_checked()

        async with self.page.expect_navigation():
            await self.page.locator("#submit-btn").click()

        form_errors = self.page.locator("#form-errors")
        await expect(form_errors).to_be_visible()
        await expect(form_errors).to_be_focused()
        await expect(form_errors).to_have_attribute("tabindex", "-1")

        error_link = form_errors.get_by_role(
            "link", name="Vous devez sélectionner au moins une démarche."
        )
        await expect(error_link).to_have_attribute("href", "#demarche-fieldset")

        demarche_fieldset = self.page.locator("#demarche-fieldset")
        await expect(demarche_fieldset).to_have_attribute("tabindex", "-1")
        described_by = await demarche_fieldset.get_attribute("aria-describedby")
        self.assertIn("demarche-hint", described_by)
        self.assertIn("id_demarche-desc-error", described_by)

        await error_link.click()
        await expect(demarche_fieldset).to_be_focused()
