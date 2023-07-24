from textwrap import dedent
from typing import Collection, Sequence
from unittest import mock
from unittest.mock import Mock

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_web.admin import MandatAdmin
from aidants_connect_web.models import Aidant, Mandat
from aidants_connect_web.tests.factories import (
    AdminFactory,
    AidantFactory,
    MandatFactory,
)


@tag("functional")
class ViewAutorisationsTests(FunctionalTestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory(
            is_superuser=True, is_staff=True, is_active=True, post__with_otp_device=True
        )

        self.aidante_fatimah = AidantFactory()

        self.mandate_1 = MandatFactory(organisation=self.aidant_thierry.organisation)
        self.mandate_2 = MandatFactory(organisation=self.aidant_thierry.organisation)
        self.mandate_3 = MandatFactory(organisation=self.aidant_thierry.organisation)
        self.mandate_4 = MandatFactory(organisation=self.aidant_thierry.organisation)

    def test_transfert_is_ok(self):
        self.open_live_url(reverse("otpadmin:aidants_connect_web_mandat_transfer"))
        self.__login()
        self.__transfer_mandate(
            [self.mandate_1, self.mandate_2], self.aidante_fatimah.organisation.pk
        )

        wait = WebDriverWait(self.selenium, 10)
        wait.until(
            url_matches(
                f"^.+{reverse('otpadmin:aidants_connect_web_mandat_changelist')}$"
            )
        )

        self.assertEqual(
            Mandat.objects.get(pk=self.mandate_1.pk).organisation,
            self.aidante_fatimah.organisation,
        )
        self.assertEqual(
            Mandat.objects.get(pk=self.mandate_2.pk).organisation,
            self.aidante_fatimah.organisation,
        )
        self.assertEqual(
            Mandat.objects.get(pk=self.mandate_3.pk).organisation,
            self.aidant_thierry.organisation,
        )
        self.assertEqual(
            Mandat.objects.get(pk=self.mandate_4.pk).organisation,
            self.aidant_thierry.organisation,
        )

    def test_resists_to_non_existent_organisation(self):
        self.open_live_url(reverse("otpadmin:aidants_connect_web_mandat_transfer"))
        self.__login()
        self.__transfer_mandate([self.mandate_1, self.mandate_2], 666)

        ids = f"{self.mandate_1.pk},{self.mandate_2.pk}"
        self.assertTrue(
            self.selenium.current_url.endswith(
                f"{reverse('otpadmin:aidants_connect_web_mandat_transfer')}?ids={ids}"
            )
        )

        self.assertEqual(
            self.selenium.find_element(
                By.CSS_SELECTOR, "ul.messagelist > li.error"
            ).text.strip(),
            "L'organisation sélectionnée n'existe pas. Veuillez corriger votre requête",
        )

    @mock.patch("aidants_connect_web.models.Mandat.transfer_to_organisation")
    def test_an_error_happens_when_transfering(self, transfer_to_organisation: Mock):
        transfer_to_organisation.side_effect = Exception("Oopsie")

        self.open_live_url(reverse("otpadmin:aidants_connect_web_mandat_transfer"))
        self.__login()
        self.__transfer_mandate(
            [self.mandate_1, self.mandate_2], self.aidante_fatimah.organisation.pk
        )

        transfer_to_organisation.stop()

        self.assertTrue(
            self.selenium.current_url.endswith(
                f"{reverse('otpadmin:aidants_connect_web_mandat_changelist')}"
            )
        )

        self.assertEqual(
            self.selenium.find_element(
                By.CSS_SELECTOR, "ul.messagelist > li.error"
            ).text.strip(),
            "Les mandats n'ont pas pu être tansférés à cause d'une erreur.",
        )

    @mock.patch("aidants_connect_web.models.Mandat.transfer_to_organisation")
    def test_some_mandates_can_t_be_transferred(self, transfer_to_organisation: Mock):
        def side_effect(_, ids: Collection):
            return len(ids) != 0, ids

        transfer_to_organisation.side_effect = side_effect

        self.open_live_url(reverse("otpadmin:aidants_connect_web_mandat_transfer"))
        self.__login()
        self.__transfer_mandate(
            [self.mandate_1, self.mandate_2], self.aidante_fatimah.organisation.pk
        )

        transfer_to_organisation.stop()

        self.assertTrue(
            self.selenium.current_url.endswith(
                f"{reverse('otpadmin:aidants_connect_web_mandat_transfer')}"
            )
        )

        self.assertEqual(
            self.selenium.find_element(By.CSS_SELECTOR, "#content h1").text.strip(),
            "⚠ Certains mandats n'ont pas pu être "
            "transférés vers la nouvelle organiation",
        )

        mandates = [
            item.text for item in self.selenium.find_elements(By.TAG_NAME, "li")
        ]
        self.assertEqual(
            mandates,
            [
                f"le mandat {self.mandate_1.template_repr},",
                f"le mandat {self.mandate_2.template_repr}.",
            ],
        )

    def __transfer_mandate(self, mandates: Sequence[Mandat], organisation: int):
        wait = WebDriverWait(self.selenium, 10)

        # Select mandates 1 & 2
        for mandate in mandates:
            self.selenium.find_element(
                By.XPATH, f"//table//input[@value='{mandate.pk}']"
            ).click()

        # Select action
        Select(
            self.selenium.find_element(
                By.XPATH, "//form[@id='changelist-form']//select[@name='action']"
            )
        ).select_by_visible_text(
            MandatAdmin.move_to_another_organisation.short_description
        )

        # Submit form
        ids = sorted([str(mandate.pk) for mandate in mandates], key=int)
        path = reverse("otpadmin:aidants_connect_web_mandat_transfer")
        self.selenium.find_element(
            By.XPATH, "//form[@id='changelist-form']//button[@type='submit']"
        ).click()
        wait.until(url_matches(f"^.+{path}\\?ids={','.join(ids)}$"))

        # Transfer to new organisation
        field = self.selenium.find_element(By.XPATH, "//input[@name='organisation']")
        field.clear()
        field.send_keys(organisation)
        self.selenium.find_element(By.XPATH, "//input[@type='submit']").click()

    def __login(self):
        field = self.selenium.find_element(By.ID, "id_username")
        field.send_keys(self.aidant_thierry.username)
        field = self.selenium.find_element(By.ID, "id_password")
        field.send_keys("motdepassedethierry")
        field = self.selenium.find_element(By.ID, "id_otp_token")
        field.send_keys("123456")
        submit_button = self.selenium.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()


@tag("functional")
class AidantAdmin(FunctionalTestCase):
    def setUp(self):
        super().setUp()
        self.password = "123456789"
        self.otp = "123456"
        self.aidant: Aidant = AdminFactory(
            password=self.password, post__with_otp_device=self.otp
        )

        self.aidants_to_deactivate = [AdminFactory(), AdminFactory(is_active=False)]

    def test_mass_deactivate_aidant_from_mail(self):
        self.admin_login(self.aidant.email, self.password, self.otp)

        self.open_live_url(reverse("otpadmin:aidants_connect_web_aidant_changelist"))

        self.wait.until(
            self.path_matches("otpadmin:aidants_connect_web_aidant_changelist")
        )

        self.selenium.find_element(
            By.XPATH, "//a[normalize-space(text())='Désactiver en masse par email']"
        ).click()

        self.wait.until(
            self.path_matches("otpadmin:aidants_connect_web_aidant_mass_deactivate")
        )

        self.selenium.find_element(By.ID, "id_email_list").send_keys(
            "\n".join(
                [
                    "karl_marx@internationale.de",
                    "friedrich_engels@internationale.de",
                    *[aidant.email for aidant in self.aidants_to_deactivate],
                ]
            )
        )

        self.selenium.find_element(By.CSS_SELECTOR, '[value="Valider"]').click()

        for aidant in self.aidants_to_deactivate:
            aidant.refresh_from_db()
            self.assertFalse(aidant.is_active)

        self.assertEqual(
            dedent(
                """
                Nous n’avons trouvé aucun aidant à désactiver pour les 2 emails suivants :
                friedrich_engels@internationale.de
                karl_marx@internationale.de
                Ces profils n’ont pas été désactivés.
                """  # noqa: E501
            ).strip(),
            self.selenium.find_element(By.CSS_SELECTOR, ".messagelist .warning").text,
        )

        self.assertEqual(
            "Nous avons désactivé 2 profils.",
            self.selenium.find_element(By.CSS_SELECTOR, ".messagelist .success").text,
        )
