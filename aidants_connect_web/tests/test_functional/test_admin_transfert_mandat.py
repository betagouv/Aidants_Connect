from typing import Sequence, Collection
from unittest import mock
from unittest.mock import Mock

from django.test import tag
from django.urls import reverse
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_web.admin import MandatAdmin
from aidants_connect_web.models import Mandat
from aidants_connect_web.tests.factories import AidantFactory, MandatFactory
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase


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
            self.selenium.find_element_by_css_selector(
                "ul.messagelist > li.error"
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
            self.selenium.find_element_by_css_selector(
                "ul.messagelist > li.error"
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
            self.selenium.find_element_by_css_selector("#content h1").text.strip(),
            "⚠ Certains mandats n'ont pas pu être "
            "transférés vers la nouvelle organiation",
        )

        mandates = [item.text for item in self.selenium.find_elements_by_tag_name("li")]
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
            self.selenium.find_element_by_xpath(
                f"//table//input[@value='{mandate.pk}']"
            ).click()

        # Select action
        Select(
            self.selenium.find_element_by_xpath(
                "//form[@id='changelist-form']//select[@name='action']"
            )
        ).select_by_visible_text(
            MandatAdmin.move_to_another_organisation.short_description
        )

        # Submit form
        ids = sorted([str(mandate.pk) for mandate in mandates], key=int)
        path = reverse("otpadmin:aidants_connect_web_mandat_transfer")
        self.selenium.find_element_by_xpath(
            "//form[@id='changelist-form']//button[@type='submit']"
        ).click()
        wait.until(url_matches(f"^.+{path}\\?ids={','.join(ids)}$"))

        # Transfer to new organisation
        field = self.selenium.find_element_by_xpath("//input[@name='organisation']")
        field.clear()
        field.send_keys(organisation)
        self.selenium.find_element_by_xpath("//input[@type='submit']").click()

    def __login(self):
        field = self.selenium.find_element_by_id("id_username")
        field.send_keys(self.aidant_thierry.username)
        field = self.selenium.find_element_by_id("id_password")
        field.send_keys("motdepassedethierry")
        field = self.selenium.find_element_by_id("id_otp_token")
        field.send_keys("123456")
        submit_button = self.selenium.find_element_by_xpath("//input[@type='submit']")
        submit_button.click()
