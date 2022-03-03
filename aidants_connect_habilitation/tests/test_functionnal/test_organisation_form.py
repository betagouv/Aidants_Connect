from typing import Optional
from uuid import uuid4

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.models import Issuer, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    IssuerFactory,
    OrganisationRequestFactory,
)


@tag("functional")
class OrganisationRequestFormViewTests(FunctionalTestCase):
    def test_form_normal_organisation(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
            public_service_delegation_attestation=False,
        )
        self.__open_form_url(issuer)

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
            "partner_administration",
            "france_services_label",
            "web_site",
            "mission_description",
            "avg_nb_demarches",
        ]:
            try:
                self.selenium.find_element(By.ID, f"id_{field}").send_keys(
                    getattr(request, field)
                )
            except Exception as e:
                raise ValueError(f"Error when setting input 'id_{field}'") from e

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(issuer.issuer_id),
                "draft_id": str(issuer.organisation_requests.first().draft_id),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def test_form_other_organisation(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.OTHER.value,
            public_service_delegation_attestation=False,
        )
        self.__open_form_url(issuer)

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        self.selenium.find_element(By.ID, "id_type_other").send_keys(request.type_other)

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
            "partner_administration",
            "france_services_label",
            "web_site",
            "mission_description",
            "avg_nb_demarches",
        ]:
            try:
                self.selenium.find_element(By.ID, f"id_{field}").send_keys(
                    getattr(request, field)
                )
            except Exception as e:
                raise ValueError(f"Error when setting input 'id_{field}'") from e

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(issuer.issuer_id),
                "draft_id": str(issuer.organisation_requests.first().draft_id),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def test_hide_type_other_input_when_org_type_is_other(self):
        issuer: Issuer = IssuerFactory()
        self.__open_form_url(issuer)

        id_type_other_el = self.selenium.find_element(By.ID, "id_type_other")
        self.assertFalse(id_type_other_el.is_displayed())

        select = Select(self.selenium.find_element(By.ID, "id_type"))
        select.select_by_visible_text(RequestOriginConstants.OTHER.label)
        self.assertTrue(id_type_other_el.is_displayed())
        self.assertEqual(
            self.selenium.find_element(
                By.CSS_SELECTOR, 'label[for="id_type_other"]'
            ).text,
            "Veuillez préciser le type d’organisation",
        )

        select.select_by_visible_text(RequestOriginConstants.MEDIATHEQUE.label)
        self.assertFalse(id_type_other_el.is_displayed())

    def test_modify_organisation_type_other_input_is_displayed(self):
        issuer: Issuer = IssuerFactory()
        organisation: OrganisationRequest = OrganisationRequestFactory(
            type_id=RequestOriginConstants.OTHER.value,
            type_other="L'organisation des travailleurs",
            draft_id=uuid4(),
        )
        self.__open_form_url(issuer, organisation)

        id_type_other_el = self.selenium.find_element(By.ID, "id_type_other")
        self.assertTrue(id_type_other_el.is_displayed())
        self.assertEqual(
            self.selenium.find_element(
                By.CSS_SELECTOR, 'label[for="id_type_other"]'
            ).text,
            "Veuillez préciser le type d’organisation",
        )
        self.assertEqual(
            self.selenium.find_element(By.ID, "id_type_other").get_attribute("value"),
            "L'organisation des travailleurs",
        )
        self.assertEqual(
            self.selenium.find_element(By.ID, "id_type").get_attribute("value"),
            str(RequestOriginConstants.OTHER.value),
        )

    def __open_form_url(
        self,
        issuer: Issuer,
        organisation_request: Optional[OrganisationRequest] = None,
    ):
        pattern = (
            "habilitation_modify_organisation"
            if organisation_request
            else "habilitation_new_organisation"
        )
        kwargs = {"issuer_id": issuer.issuer_id}
        if organisation_request:
            kwargs.update(draft_id=organisation_request.draft_id)
        self.open_live_url(reverse(pattern, kwargs=kwargs))
