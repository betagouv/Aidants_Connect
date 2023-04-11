from datetime import timedelta

from django.db import transaction
from django.test import override_settings, tag
from django.urls import reverse
from django.utils import formats, timezone

from freezegun import freeze_time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_pico_cms.models import MandateTranslation
from aidants_connect_web.models import Mandat
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    UsagerFactory,
)


@tag("functional", "renew_mandat")
@override_settings(FF_MANDATE_TRANSLATION=True)
class DisplayTranslationTests(FunctionalTestCase):
    def setUp(self):
        self.aidant = AidantFactory(post__with_otp_device=True)
        with transaction.atomic():
            # Start on an empty DB for these tests
            MandateTranslation.objects.all().delete()

    @freeze_time("2020-01-01 07:00:00")
    def test_display_attestation(self):
        self.open_live_url(reverse("new_mandat"))
        self.login_aidant(self.aidant)

        demarches_section = self.selenium.find_element(By.ID, "demarches")

        demarches_section.find_element(By.ID, "argent").find_element(
            By.TAG_NAME, "label"
        ).click()
        demarches_section.find_element(By.ID, "famille").find_element(
            By.TAG_NAME, "label"
        ).click()

        duree_section = self.selenium.find_element(By.ID, "duree")
        duree_section.find_element(By.ID, "SHORT").find_element(
            By.TAG_NAME, "label"
        ).click()

        self.selenium.find_element(
            By.CSS_SELECTOR, ".mandate-translation-section a"
        ).click()

        self.wait.until(self.path_matches("mandate_translation"))

        mandat = self.selenium.find_element(By.CSS_SELECTOR, ".container")

        self.assertInHTML(
            "FAMILLE: Allocations familiales, Naissance, Mariage, Pacs, Scolarité…",
            mandat.get_attribute("innerHTML"),
        )

        self.assertInHTML(
            "ARGENT: Crédit immobilier, Impôts, Consommation, "
            "Livret A, Assurance, Surendettement…",
            mandat.get_attribute("innerHTML"),
        )

        self.assertInHTML(
            formats.date_format(timezone.now(), "l j F Y"),
            mandat.get_attribute("innerHTML"),
        )

    def test_display_translation_for_new_mandat(self):
        self.lang: MandateTranslation = MandateTranslation.objects.create(
            lang="pus", body="# Test title\n\nTest"
        )

        self.open_live_url(reverse("new_mandat"))
        self.login_aidant(self.aidant)

        demarches_section = self.selenium.find_element(By.ID, "demarches")

        demarches_section.find_element(By.ID, "argent").find_element(
            By.TAG_NAME, "label"
        ).click()
        demarches_section.find_element(By.ID, "famille").find_element(
            By.TAG_NAME, "label"
        ).click()

        duree_section = self.selenium.find_element(By.ID, "duree")
        duree_section.find_element(By.ID, "SHORT").find_element(
            By.TAG_NAME, "label"
        ).click()

        self.selenium.find_element(
            By.CSS_SELECTOR, ".mandate-translation-section a"
        ).click()

        self.wait.until(self.path_matches("mandate_translation"))

        self.assertInHTML(
            "D'autres langues sont disponibles",
            self.selenium.find_element(
                By.CSS_SELECTOR, ".mandate-translation-other"
            ).get_attribute("innerHTML"),
        )

        select = Select(
            self.selenium.find_element(By.CSS_SELECTOR, "#mandate-translation-lang")
        )

        select.select_by_visible_text(self.lang.lang_name)

        translation_container = self.selenium.find_element(
            By.CSS_SELECTOR, ".mandate-translation-other"
        )

        self.assertHTMLEqual(
            f'<section class="container" dir="rtl">{self.lang.to_html()}</section>',
            translation_container.get_attribute("innerHTML"),
        )

        self.assertEqual("pus", translation_container.get_attribute("lang"))

    def test_display_translation_for_renew_mandat(self):
        self.lang: MandateTranslation = MandateTranslation.objects.create(
            lang="pus", body="# Test title\n\nTest"
        )

        self.open_live_url(reverse("new_mandat"))
        self.login_aidant(self.aidant)

        self.usager = UsagerFactory(given_name="Fabrice")
        MandatFactory(
            organisation=self.aidant.organisation,
            usager=self.usager,
            expiration_date=timezone.now() + timedelta(days=5),
        )

        self.assertEqual(Mandat.objects.filter(usager=self.usager).count(), 1)

        self.open_live_url(f"/renew_mandat/{self.usager.pk}")

        demarches_section = self.selenium.find_element(By.ID, "demarches")

        demarches_section.find_element(By.ID, "argent").find_element(
            By.TAG_NAME, "label"
        ).click()
        demarches_section.find_element(By.ID, "famille").find_element(
            By.TAG_NAME, "label"
        ).click()

        duree_section = self.selenium.find_element(By.ID, "duree")
        duree_section.find_element(By.ID, "SHORT").find_element(
            By.TAG_NAME, "label"
        ).click()

        self.selenium.find_element(
            By.CSS_SELECTOR, ".mandate-translation-section a"
        ).click()

        self.wait.until(self.path_matches("mandate_translation"))

        self.assertInHTML(
            "D'autres langues sont disponibles",
            self.selenium.find_element(
                By.CSS_SELECTOR, ".mandate-translation-other"
            ).get_attribute("innerHTML"),
        )

        select = Select(
            self.selenium.find_element(By.CSS_SELECTOR, "#mandate-translation-lang")
        )

        select.select_by_visible_text(self.lang.lang_name)

        translation_container = self.selenium.find_element(
            By.CSS_SELECTOR, ".mandate-translation-other"
        )

        self.assertTrue(
            translation_container.is_displayed(),
            "Container .mandate-translation-other should be visible",
        )

        self.assertHTMLEqual(
            f'<section class="container" dir="rtl">{self.lang.to_html()}</section>',
            translation_container.get_attribute("innerHTML"),
        )

        self.assertEqual("pus", translation_container.get_attribute("lang"))
