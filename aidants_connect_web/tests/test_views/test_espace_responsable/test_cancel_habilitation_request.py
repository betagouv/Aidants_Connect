from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse

from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class CancelHabilitationRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        # Create one référent
        cls.organisation1 = OrganisationFactory()
        cls.organisation2 = OrganisationFactory()
        cls.responsable = AidantFactory(
            organisation=cls.organisation1, post__is_organisation_manager=True
        )

        for count, org in enumerate([cls.organisation1, cls.organisation2]):
            for status in ReferentRequestStatuses:
                setattr(
                    cls,
                    f"org{count + 1}_{status.value}",
                    HabilitationRequestFactory(organisation=org, status=status),
                )

    def test_triggers_correct_view(self):
        found = resolve(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org1_processing.pk},
            )
        )
        self.assertEqual(
            found.func.view_class, espace_responsable.CancelHabilitationRequestView
        )

    def test_renders_correct_template(self):
        self.client.force_login(self.responsable)
        response = self.client.get(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org1_processing.pk},
            )
        )
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/cancel-habilitation-request.html",
        )

    def test_cant_cancel_not_owned_request(self):
        self.client.force_login(self.responsable)
        response = self.client.get(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org2_processing.pk},
            )
        )
        self.assertEqual(404, response.status_code)

        response = self.client.post(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org2_processing.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_cant_cancel_not_cancelable_request(self):
        self.client.force_login(self.responsable)
        response = self.client.get(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org2_cancelled.pk},
            )
        )
        self.assertEqual(404, response.status_code)

        response = self.client.post(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org2_cancelled.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_cancel_request(self):
        self.client.force_login(self.responsable)
        response = self.client.post(
            reverse(
                "espace_responsable_cancel_habilitation",
                kwargs={"request_id": self.org1_waitling_list.pk},
            )
        )
        self.assertRedirects(
            response,
            reverse("espace_responsable_organisation"),
            fetch_redirect_response=False,
        )
        self.org1_waitling_list.refresh_from_db()
        self.assertEqual(
            self.org1_waitling_list.status,
            ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE,
        )
