from django.test import TestCase, tag
from django.urls import resolve, reverse

from faker.proxy import Faker

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_habilitation.api.views import PersonnelRequestEditView
from aidants_connect_habilitation.forms import AidantRequestForm
from aidants_connect_habilitation.models import AidantRequest, OrganisationRequest
from aidants_connect_habilitation.tests.factories import (
    AidantRequestFactory,
    OrganisationRequestFactory,
)


@tag("habilitation", "api")
class HabilitationRequestsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faker = Faker()

        cls.org: OrganisationRequest = OrganisationRequestFactory(
            status=RequestStatusConstants.NEW
        )
        cls.aidant_req1: AidantRequest = AidantRequestFactory(organisation=cls.org)
        cls.aidant_req2: AidantRequest = AidantRequestFactory(organisation=cls.org)

        cls.unmodifiable_orgs = [
            OrganisationRequestFactory(status=status, post__aidants_count=1)
            for status in (
                set(RequestStatusConstants)
                - set(RequestStatusConstants.aidant_registrable)
            )
        ]

    def test_triggers_the_right_view(self):
        found = resolve(self._get_url(self.aidant_req1))
        self.assertEqual(found.func.view_class, PersonnelRequestEditView)

    def test_renders_the_right_template(self):
        with self.subTest("GET"):
            response = self.client.get(self._get_url(self.aidant_req1))
            self.assertTemplateUsed(response, "forms/form.html")

        with self.subTest("POST with errors"):
            response = self.client.post(self._get_url(self.aidant_req1), data={})
            self.assertEqual(response.status_code, 422)
            self.assertTemplateUsed(response, "forms/form.html")

        with self.subTest("POST without errors"):
            response = self.client.post(
                self._get_url(self.aidant_req1),
                data=self._get_valid_data(
                    self.aidant_req1, email=self._get_new_valid_email(self.aidant_req1)
                ),
            )
            self.assertEqual(response.status_code, 200)
            # self.assertTemplateUsed is not working with django-template-partials
            self.assertEqual(
                set(response.template_name),
                {
                    "habilitation/generic-habilitation-request-profile-card.html"
                    "#habilitation-profile-card"
                },
            )

    def test_404_on_aidant_not_registrable(self):
        with self.subTest("GET"):
            for organisation in self.unmodifiable_orgs:
                aidant = organisation.aidant_requests.first()
                with self.subTest(f"{organisation.status}"):
                    response = self.client.get(self._get_url(aidant))
                    self.assertEqual(404, response.status_code)

        with self.subTest("POST"):
            for organisation in self.unmodifiable_orgs:
                aidant = organisation.aidant_requests.first()
                new_email = self._get_new_valid_email(aidant)
                with self.subTest(f"{organisation.status}"):
                    response = self.client.get(
                        self._get_url(aidant),
                        data=self._get_valid_data(self.aidant_req1, email=new_email),
                    )
                    self.assertEqual(404, response.status_code)

    def test_post(self):
        with self.subTest("with errors"):
            response = self.client.post(
                self._get_url(self.aidant_req1),
                data=self._get_valid_data(
                    self.aidant_req1, email=self.aidant_req2.email
                ),
            )
            self.assertEqual(response.status_code, 422)
            self.aidant_req1.refresh_from_db()
            self.assertNotEqual(self.aidant_req1.email, self.aidant_req2.email)

        with self.subTest("with valid data"):
            new_email = self._get_new_valid_email(self.aidant_req1)
            response = self.client.post(
                self._get_url(self.aidant_req1),
                data=self._get_valid_data(self.aidant_req1, email=new_email),
            )
            self.assertEqual(response.status_code, 200)
            self.aidant_req1.refresh_from_db()
            self.assertEqual(new_email, self.aidant_req1.email)

    def test_delete(self):
        self.assertEqual(AidantRequest.objects.filter(organisation=self.org).count(), 2)
        response = self.client.delete(self._get_url(self.aidant_req1))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(AidantRequest.objects.filter(organisation=self.org).count(), 1)

    def _get_url(self, request: AidantRequest):
        return reverse(
            "api_habilitation_aidant_edit",
            kwargs={
                "issuer_id": request.organisation.issuer.issuer_id,
                "uuid": request.organisation.uuid,
                "aidant_id": request.pk,
            },
        )

    def _get_new_valid_email(self, request: AidantRequest):
        for _ in range(10):
            new_email = self.faker.email()
            if new_email not in (
                request.organisation.aidant_requests.values_list("email", flat=True)
            ):
                return new_email

        self.fail("This shouldn't happen")

    def _get_valid_data(self, request: AidantRequest, **kwargs):
        return {
            **AidantRequestForm(organisation=self.org, instance=request).initial,
            **kwargs,
        }
