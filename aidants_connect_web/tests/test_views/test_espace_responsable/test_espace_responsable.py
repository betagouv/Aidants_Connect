from django.contrib import messages as django_messages
from django.test import TestCase, tag
from django.test.client import Client
from django.urls import resolve, reverse

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure")
class EspaceResponsableOrganisationPage(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.responsable_tom = AidantFactory()
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.id_organisation = cls.responsable_tom.organisation.id
        cls.autre_organisation = OrganisationFactory()

    def test_espace_responsable_organisation_url_triggers_the_right_view(self):
        self.client.force_login(self.responsable_tom)
        found = resolve("/espace-responsable/organisation/")
        self.assertEqual(found.func.view_class, espace_responsable.OrganisationView)

    def test_espace_responsable_organisation_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get("/espace-responsable/organisation/")
        self.assertEqual(
            response.status_code,
            200,
            "trying to get " "/espace-responsable/organisation/",
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/organisation.html"
        )

    def test_display_all_active_aidants(self):
        self.client.force_login(self.responsable_tom)
        aidant_a = AidantFactory(
            first_name="Premier-Aidant", organisation=self.responsable_tom.organisation
        )
        aidant_b = AidantFactory(first_name="Second-Aidant")
        aidant_b.organisations.set(
            (aidant_b.organisation, self.responsable_tom.organisation)
        )
        response = self.client.get("/espace-responsable/organisation/")
        self.assertContains(response, aidant_a.first_name)
        self.assertContains(response, aidant_b.first_name)

    def test_display_organisation_properly(self):
        self.client.force_login(self.responsable_tom)
        organisation = OrganisationFactory(city=None)
        self.responsable_tom.responsable_de.add(organisation)
        response = self.client.get("/espace-responsable/organisation/")
        self.assertNotContains(response, "None")

    def test_display_data_pass_id(self):
        self.client.force_login(self.responsable_tom)
        self.responsable_tom.organisation.data_pass_id = 4242
        self.responsable_tom.organisation.save()
        response = self.client.get("/espace-responsable/organisation/")
        self.assertContains(response, "Numéro d’habilitation")
        self.assertContains(response, "4242")

    def test_hide_block_if_no_data_pass_id(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get("/espace-responsable/organisation/")
        self.assertNotContains(response, "Numéro d’habilitation")


@tag("responsable-structure")
class EspaceResponsableAidantPage(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.responsable_tom = AidantFactory()
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)
        cls.aidant_tim = AidantFactory(organisation=cls.responsable_tom.organisation)
        cls.aidant_tim_url = f"/espace-responsable/aidant/{cls.aidant_tim.id}/"
        cls.autre_organisation = OrganisationFactory()
        cls.autre_aidant = AidantFactory()

    def test_espace_responsable_aidant_url_triggers_the_right_view(self):
        self.client.force_login(self.responsable_tom)
        found = resolve(self.aidant_tim_url)
        self.assertEqual(found.func.view_class, espace_responsable.AidantView)

    def test_espace_responsable_aidant_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.aidant_tim_url)
        self.assertEqual(
            response.status_code,
            200,
            f"trying to get {self.aidant_tim_url}",
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/aidant.html"
        )

    def test_responsable_cannot_see_an_aidant_they_are_not_responsible_for(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(
            f"/espace-responsable/aidant/{self.autre_aidant.id}/"
        )
        self.assertRedirects(response, reverse("espace_responsable_organisation"))
        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            "Ce profil aidant nʼexiste pas ou nʼest pas membre de votre organisation "
            "active. Si ce profil existe et que vous faites partie de ses référents, "
            "veuillez changer dʼorganisation pour le gérer.",
            messages[0].message,
        )


@tag("responsable-structure")
class EspaceResponsableChangeAidantOrganisationsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        responsable = AidantFactory()
        responsable.responsable_de.add(responsable.organisation)
        responsable.responsable_de.add(OrganisationFactory())
        cls.responsable_of_2 = responsable

        responsable = AidantFactory()
        responsable.responsable_de.add(responsable.organisation)
        cls.responsable_of_1 = responsable

    def get_aidant_url(self, aidant):
        return f"/espace-responsable/aidant/{aidant.id}/"

    def get_form_url(self, aidant):
        return f"/espace-responsable/aidant/{aidant.id}/changer-organisations/"

    def test_responsable_of_one_structure_cannot_see_the_form(self):
        responsable = self.responsable_of_1
        aidant = AidantFactory(organisation=responsable.organisation)
        self.client.force_login(responsable)

        response = self.client.get(self.get_aidant_url(aidant))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Changer les organisations de rattachement")

    def test_responsable_of_several_structures_can_see_the_form(self):
        responsable = self.responsable_of_2
        aidant = AidantFactory(organisation=responsable.organisation)
        self.client.force_login(responsable)

        url = self.get_aidant_url(aidant)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Changer les organisations de rattachement")

    def test_organisations_are_modified(self):
        responsable = self.responsable_of_2
        aidant = AidantFactory(organisation=responsable.organisation)
        self.client.force_login(responsable)

        self.assertEqual(len(aidant.organisations.all()), 1)
        response = self.client.post(
            self.get_form_url(aidant),
            {"organisations": [org.id for org in responsable.responsable_de.all()]},
        )
        self.assertRedirects(response, reverse("espace_responsable_organisation"))
        aidant.refresh_from_db()
        self.assertEqual(len(aidant.organisations.all()), 2)
        self.assertTrue(
            all(
                org in aidant.organisations.all()
                for org in responsable.responsable_de.all()
            )
        )

    def test_active_organisation_is_switched_if_necessary(self):
        responsable = self.responsable_of_2
        first_org, other_org = responsable.responsable_de.all()

        aidant = AidantFactory(organisation=first_org)
        self.assertEqual(len(aidant.organisations.all()), 1)
        self.assertIn(first_org, aidant.organisations.all())

        self.client.force_login(responsable)
        response = self.client.post(
            self.get_form_url(aidant),
            {"organisations": [other_org.id]},
        )
        self.assertRedirects(response, reverse("espace_responsable_organisation"))

        aidant.refresh_from_db()
        self.assertEqual(
            len(aidant.organisations.all()),
            1,
            "Aidant’s organisations should contain only one organisation.",
        )
        self.assertIn(other_org, aidant.organisations.all())
        self.assertEqual(aidant.organisation, other_org)

    def test_responsable_cannot_change_an_unrelated_organisation_on_their_aidants(self):
        responsable = self.responsable_of_2
        respo_org_1, respo_org_2 = responsable.responsable_de.all()
        aidant = AidantFactory()
        aidant_initial_org = aidant.organisation
        aidant.organisations.add(respo_org_1)

        self.assertIn(aidant_initial_org, aidant.organisations.all())
        self.assertIn(respo_org_1, aidant.organisations.all())
        self.assertEqual(len(aidant.organisations.all()), 2)

        self.client.force_login(responsable)
        self.client.post(
            self.get_form_url(aidant),
            {"organisations": [respo_org_1.id, respo_org_2.id]},
        )

        aidant.refresh_from_db()
        self.assertIn(aidant_initial_org, aidant.organisations.all())
        self.assertIn(respo_org_1, aidant.organisations.all())
        self.assertIn(respo_org_2, aidant.organisations.all())
        self.assertEqual(
            len(aidant.organisations.all()),
            3,
            "Aidant’s organisations should contain 3 organisations.",
        )
        self.assertEqual(aidant.organisation, aidant_initial_org)

    def test_responsable_cannot_change_orgs_of_unrelated_aidant(self):
        responsable = self.responsable_of_2
        aidant = AidantFactory()

        self.client.force_login(responsable)
        response = self.client.post(
            self.get_form_url(aidant),
            {"organisations": [responsable.organisation.id]},
        )
        self.assertRedirects(response, reverse("espace_responsable_organisation"))
        messages = list(django_messages.get_messages(response.wsgi_request))
        self.assertEqual(
            "Ce profil aidant nʼexiste pas ou nʼest pas membre de votre organisation "
            "active. Si ce profil existe et que vous faites partie de ses référents, "
            "veuillez changer dʼorganisation pour le gérer.",
            messages[0].message,
        )


@tag("responsable-structure")
class EspaceResponsableAddAidant(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.responsable_tom = AidantFactory()
        cls.responsable_tom.responsable_de.add(cls.responsable_tom.organisation)

        cls.id_organisation = cls.responsable_tom.organisation.id
        cls.add_aidant_url = "/espace-responsable/aidant/ajouter/"
        cls.autre_organisation = OrganisationFactory()

    def test_add_aidant_url_triggers_the_right_view(self):
        self.client.force_login(self.responsable_tom)
        found = resolve(self.add_aidant_url)
        self.assertEqual(
            found.func.view_class, espace_responsable.NewHabilitationRequest
        )

    def test_add_aidant_url_triggers_the_right_template(self):
        self.client.force_login(self.responsable_tom)
        response = self.client.get(self.add_aidant_url)
        self.assertEqual(
            response.status_code,
            200,
            f"trying to get {self.add_aidant_url}",
        )
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/new-habilitation-request.html",
        )


@tag("responsable-structure")
class InsistOnTOTPDeviceActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        orga = OrganisationFactory()
        # Mario is a référent without TOTP Device activated
        # => He should see the messages
        cls.responsable_mario = AidantFactory(
            username="mario@brosse.fr", organisation=orga
        )
        cls.responsable_mario.responsable_de.add(cls.responsable_mario.organisation)
        cls.responsable_mario.responsable_de.add(OrganisationFactory())
        # Mickey is a référent with a TOTP Device activated
        # => He should not see the messages
        cls.responsable_mickey = AidantFactory(
            username="mickey@mousse.fr", organisation=orga
        )
        cls.responsable_mickey.responsable_de.add(cls.responsable_mickey.organisation)
        cls.responsable_mickey.responsable_de.add(OrganisationFactory())
        device = TOTPDevice(user=cls.responsable_mickey)
        device.save()
        # Roger is a référent with an *inactive* TOTP Device
        # (e.g. after an unfinished card activation)
        # => He should see the messages
        cls.responsable_hubert = AidantFactory(
            username="hubert@lingot.fr", organisation=orga
        )
        cls.responsable_hubert.responsable_de.add(cls.responsable_hubert.organisation)
        cls.responsable_hubert.responsable_de.add(OrganisationFactory())
        device = TOTPDevice(user=cls.responsable_hubert, confirmed=False)
        device.save()
        # Guy has no TOTP Device but is a simple Aidant
        # => He should not see the messages.
        cls.aidant_guy = AidantFactory(username="guy@mauve.fr")

        cls.urls_responsables = (
            "/espace-aidant/",
            "/espace-responsable/organisation/",
        )

    def test_display_messages_to_reponsable_if_no_totp_device_exists(self):
        self.client.force_login(self.responsable_mario)
        for page in self.urls_responsables:
            response = self.client.get(page)
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "activer votre carte Aidants Connect",
                response_content,
                f"TOTP message is hidden on '{page}', it should be visible",
            )

    def test_display_messages_to_reponsable_if_the_totp_device_is_unconfirmed(self):
        self.client.force_login(self.responsable_hubert)
        for page in self.urls_responsables:
            response = self.client.get(page)
            response_content = response.content.decode("utf-8")
            self.assertIn(
                "activer votre carte Aidants Connect",
                response_content,
                f"TOTP message is hidden on '{page}', it should be visible",
            )

    def test_hide_messages_from_reponsable_if_any_totp_device_is_activated(self):
        self.client.force_login(self.responsable_mickey)
        for page in self.urls_responsables:
            response = self.client.get(page)
            response_content = response.content.decode("utf-8")
            self.assertNotIn(
                "activer votre carte Aidants Connect",
                response_content,
                f"TOTP message is shown on '{page}', it should be hidden",
            )

    def test_hide_messages_from_aidants_even_without_totp_device(self):
        self.client.force_login(self.aidant_guy)
        response = self.client.get("/espace-aidant/")
        response_content = response.content.decode("utf-8")
        self.assertNotIn(
            "activer votre carte Aidants Connect",
            response_content,
            "TOTP message is shown on espace-aidant, it should be hidden",
        )


@tag("responsable-structure")
class DesignationOfAnotherResponsable(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.orga = OrganisationFactory()
        cls.respo = AidantFactory(organisation=cls.orga)
        cls.respo.responsable_de.add(cls.orga)
        cls.orga2 = OrganisationFactory()

        cls.respo_without_aidants = AidantFactory()
        cls.respo_without_aidants.responsable_de.add(
            cls.respo_without_aidants.organisation
        )

        cls.url = reverse(
            "espace_responsable_organisation_responsables",
            kwargs={"organisation_id": cls.orga.pk},
        )
        cls.orga_url = reverse("espace_responsable_organisation")

        cls.aidante_maxine = AidantFactory(organisation=cls.orga)
        cls.aidante_ariane = AidantFactory()
        cls.aidante_ariane.organisations.add(cls.orga)

    def test_url_triggers_the_right_view(self):
        found = resolve(self.url)
        self.assertEqual(
            found.func.view_class, espace_responsable.OrganisationResponsables
        )

    def test_url_triggers_the_right_template(self):
        self.client.force_login(self.respo)
        response = self.client.get(self.url)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/responsables.html"
        )

    def test_404_on_foreign_organisation(self):
        self.client.force_login(self.respo)
        response = self.client.get(
            reverse(
                "espace_responsable_organisation_responsables",
                kwargs={"organisation_id": self.orga2.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_link_is_hidden_if_there_is_no_aidant_to_become_responsable(self):
        self.client.force_login(self.respo_without_aidants)
        response = self.client.get(
            reverse(
                "espace_responsable_organisation_responsables",
                kwargs={"organisation_id": self.respo_without_aidants.organisation.pk},
            )
        )
        self.assertNotContains(response, "Désigner un ou une référente")

    def test_link_is_visible_if_there_is_an_aidant_to_become_responsable(self):
        self.client.force_login(self.respo)
        response = self.client.get(self.orga_url)
        self.assertContains(response, "Désigner un ou une référente")

    def test_current_aidant_can_become_responsable(self):
        self.client.force_login(self.respo)
        self.assertFalse(self.aidante_maxine.is_responsable_structure())
        self.client.post(self.url, data={"candidate": self.aidante_maxine.id})
        self.aidante_maxine.refresh_from_db()
        self.assertTrue(self.aidante_maxine.is_responsable_structure())
        self.assertIn(self.orga, self.aidante_maxine.responsable_de.all())

    def test_aidant_can_become_responsable(self):
        self.client.force_login(self.respo)
        self.assertFalse(self.aidante_ariane.is_responsable_structure())
        self.client.post(self.url, data={"candidate": self.aidante_ariane.id})
        self.aidante_ariane.refresh_from_db()
        self.assertTrue(self.aidante_ariane.is_responsable_structure())
        self.assertIn(self.orga, self.aidante_ariane.responsable_de.all())

    def test_unrelated_aidant_cannot_become_responsable(self):
        self.aidante_bidule = AidantFactory()
        self.client.force_login(self.respo)
        self.assertFalse(self.aidante_bidule.is_responsable_structure())
        self.client.post(self.url, data={"candidate": self.aidante_bidule.id})
        self.aidante_bidule.refresh_from_db()
        self.assertFalse(self.aidante_bidule.is_responsable_structure())
        self.assertNotIn(self.orga, self.aidante_bidule.responsable_de.all())

    def test_disabled_aidant_cannot_become_responsable(self):
        self.aidante_bidule = AidantFactory(is_active=False)
        self.client.force_login(self.respo)
        self.assertFalse(self.aidante_bidule.is_responsable_structure())
        self.client.post(self.url, data={"candidate": self.aidante_bidule.id})
        self.aidante_bidule.refresh_from_db()
        self.assertFalse(self.aidante_bidule.is_responsable_structure())
        self.assertNotIn(self.orga, self.aidante_bidule.responsable_de.all())
