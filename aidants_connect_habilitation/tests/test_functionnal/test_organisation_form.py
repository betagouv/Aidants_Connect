from typing import List, Optional
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import modify_settings, override_settings, tag
from django.urls import reverse

from faker import Faker
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_common.utils.constants import RequestOriginConstants
from aidants_connect_common.utils.gouv_address_api import Address
from aidants_connect_habilitation.models import Issuer, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    DraftOrganisationRequestFactory,
    IssuerFactory,
    OrganisationRequestFactory,
)
from aidants_connect_habilitation.tests.utils import load_json_fixture

FIXED_PORT = 34567


def _django_server_url(path):
    return f"http://localhost:{FIXED_PORT}{path}"


@tag("functional")
class OrganisationRequestFormViewTests(FunctionalTestCase):
    port = FIXED_PORT

    def test_form_normal_organisation_with_fs_label(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
            france_services_number=444888555,
        )
        self._open_form_url(issuer)

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )
        self.selenium.find_element(By.ID, "id_france_services_label").click()

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
            "france_services_number",  # only needed if france_service_label=True
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
                "uuid": str(issuer.organisation_requests.first().uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def test_form_other_type_and_private_organisation(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.OTHER.value,
            partner_administration="Beta.Gouv",
        )
        self._open_form_url(issuer)

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        self.selenium.find_element(By.ID, "id_type_other").send_keys(request.type_other)
        self.selenium.find_element(By.ID, "id_is_private_org").click()

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
            "partner_administration",  # needed only if is_private_org=True
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
                "uuid": str(issuer.organisation_requests.first().uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

    def test_hide_type_other_input_when_org_type_is_other(self):
        issuer: Issuer = IssuerFactory()
        self._open_form_url(issuer)

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
        organisation: OrganisationRequest = DraftOrganisationRequestFactory(
            type_id=RequestOriginConstants.OTHER.value,
            type_other="L'organisation des travailleurs",
            issuer=issuer,
        )
        self._open_form_url(issuer, organisation)

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

    def test_submit_both_known_organisation_type_and_other_type(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
        )
        self._open_form_url(issuer)

        # Fill the `type_other` field
        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(RequestOriginConstants.OTHER.value)
        )

        self.selenium.find_element(By.ID, "id_type_other").send_keys(Faker().company())

        self.assertNotEqual(
            self.selenium.find_element(By.ID, "id_type_other").get_attribute("value"),
            "",
        )

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
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
                "uuid": str(issuer.organisation_requests.first().uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))
        self.assertEqual(issuer.organisation_requests.first().type, request.type)
        self.assertEqual(issuer.organisation_requests.first().type_other, "")

    @override_settings(
        GOUV_ADDRESS_SEARCH_API_DISABLED=False,
        GOUV_ADDRESS_SEARCH_API_BASE_URL=_django_server_url(
            reverse("address_api_segur")
        ),
    )
    @modify_settings(
        CSP_CONNECT_SRC={"append": _django_server_url(reverse("address_api_segur"))},
        CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
    )
    def test_js_I_must_select_a_correct_address(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.OTHER.value,
            partner_administration="Beta.Gouv",
        )
        self._open_form_url(issuer)

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        self.selenium.find_element(By.ID, "id_type_other").send_keys(request.type_other)
        self.selenium.find_element(By.ID, "id_is_private_org").click()

        for field in [
            "name",
            "siret",
            "partner_administration",  # needed only if is_private_org=True
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

        # Open dropdown
        selected_address = "Avenue de Ségur 75007 Paris"
        self.selenium.find_element(By.CSS_SELECTOR, "#id_address").send_keys(
            selected_address
        )

        # Select result
        self.selenium.find_element(
            By.XPATH, f"//*[normalize-space(text())='{selected_address}']"
        ).click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(issuer.issuer_id),
                "uuid": str(issuer.organisation_requests.first().uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation: OrganisationRequest = issuer.organisation_requests.first()

        self.assertEqual(organisation.address, "Avenue de Ségur")
        self.assertEqual(organisation.zipcode, "75007")
        self.assertEqual(organisation.city, "Paris")
        self.assertEqual(organisation.city_insee_code, "75107")

    @override_settings(
        GOUV_ADDRESS_SEARCH_API_DISABLED=False,
        GOUV_ADDRESS_SEARCH_API_BASE_URL=_django_server_url(
            reverse("address_api_no_result")
        ),
    )
    @modify_settings(
        CSP_CONNECT_SRC={
            "append": _django_server_url(reverse("address_api_no_result"))
        },
        CSP_SCRIPT_SRC={"append": settings.AUTOCOMPLETE_SCRIPT_SRC},
    )
    def test_js_I_can_submit_an_address_that_is_not_found(self):
        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.OTHER.value,
            partner_administration="Beta.Gouv",
        )
        self._open_form_url(issuer)

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        self.selenium.find_element(By.ID, "id_type_other").send_keys(request.type_other)
        self.selenium.find_element(By.ID, "id_is_private_org").click()

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
            "web_site",
            "partner_administration",  # needed only if is_private_org=True
            "mission_description",
            "avg_nb_demarches",
        ]:
            try:
                self.selenium.find_element(By.ID, f"id_{field}").send_keys(
                    getattr(request, field)
                )
            except Exception as e:
                raise ValueError(f"Error when setting input 'id_{field}'") from e

        # Open dropdown
        self.selenium.find_element(By.CSS_SELECTOR, "#id_address").click()

        self.assertEqual(
            f"Aucun résultat trouvé pour la requête « {request.address} »",
            self.selenium.find_element(By.CSS_SELECTOR, ".no-result").text,
        )

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(issuer.issuer_id),
                "uuid": str(issuer.organisation_requests.first().uuid),
            },
        )

        WebDriverWait(self.selenium, 10).until(url_matches(f"^.+{path}$"))

        organisation: OrganisationRequest = issuer.organisation_requests.first()
        self.assertEqual(organisation.address, request.address)
        self.assertEqual(organisation.zipcode, request.zipcode)
        self.assertEqual(organisation.city, request.city)

    def _open_form_url(
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
            kwargs.update(uuid=organisation_request.uuid)
        self.open_live_url(reverse(pattern, kwargs=kwargs))


@tag("functional")
class PersonnelRequestFormViewNoJSTests(FunctionalTestCase):
    js = False

    @override_settings(GOUV_ADDRESS_SEARCH_API_DISABLED=False)
    @patch("aidants_connect_habilitation.forms.search_adresses")
    def test_I_must_select_a_correct_address(self, search_adresses_mock: Mock):
        expected_address = "Rue de Paris 45000 Orléans"
        selected_address = "Rue du Parc 45000 Orléans"

        def search_adresses(query_string: str) -> List[Address]:
            if query_string == expected_address:
                result = [
                    Address(**item["properties"])
                    for item in load_json_fixture("address_results.json")["features"]
                ]
                return result

            self.fail(f"Expected organisation with address '{expected_address}'")

        search_adresses_mock.side_effect = search_adresses

        issuer: Issuer = IssuerFactory()
        request: OrganisationRequest = OrganisationRequestFactory.build(
            type_id=RequestOriginConstants.MEDIATHEQUE.value,
            address="Rue de Paris",
            zipcode="45000",
            city="Orléans",
        )
        self._open_form_url(issuer)

        # Fill the `type_other` field
        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(RequestOriginConstants.OTHER.value)
        )

        self.selenium.find_element(By.ID, "id_type_other").send_keys(Faker().company())

        self.assertNotEqual(
            self.selenium.find_element(By.ID, "id_type_other").get_attribute("value"),
            "",
        )

        Select(self.selenium.find_element(By.ID, "id_type")).select_by_value(
            str(request.type.id)
        )

        for field in [
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
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

        self.selenium.find_element(
            By.XPATH,
            "//*[@id='id_alternative_address']"
            f"//*[normalize-space(text())='{selected_address}']",
        ).click()

        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        organisation: OrganisationRequest = issuer.organisation_requests.first()
        path = reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(issuer.issuer_id),
                "uuid": str(organisation.uuid),
            },
        )

        WebDriverWait(self.selenium, 10000).until(url_matches(f"^.+{path}$"))

        organisation.refresh_from_db()
        self.assertEqual(
            selected_address,
            f"{organisation.address} {organisation.zipcode} {organisation.city}",
        )

        # assert code INSEE
        self.assertEqual("45234", organisation.city_insee_code)

    def _open_form_url(
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
            kwargs.update(uuid=organisation_request.uuid)
        self.open_live_url(reverse(pattern, kwargs=kwargs))
