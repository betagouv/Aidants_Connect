from uuid import uuid4

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By

from aidants_connect.common.tests.testcases import FunctionalTestCase
from aidants_connect_habilitation.forms import IssuerForm
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory


@tag("functional")
class AidantsRequestFormViewTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pattern_name = "habilitation_new_aidants"
        cls.organisation: OrganisationRequest = OrganisationRequestFactory(
            draft_id=uuid4()
        )

    def open_url_from_pattern(self, org: OrganisationRequest):
        self.open_live_url(
            reverse(
                self.pattern_name,
                kwargs={
                    "issuer_id": org.issuer.issuer_id,
                    "draft_id": org.draft_id,
                },
            )
        )

    def test_issuer_form_is_rendered_harmless(self):
        self.open_url_from_pattern(self.organisation)

        for name in IssuerForm().fields.keys():
            el_id = f"id_{name}"
            el = self.selenium.find_element(By.ID, el_id)
            el_name_attr = el.get_attribute("name")
            self.assertEqual(
                el_name_attr,
                "",
                f"""Element <{el.tag_name} id="{el_id}"> from issuer form should not """
                f"have `name` attribute set (current value is '{el_name_attr}')",
            )
