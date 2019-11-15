import io
import PyPDF2
from pytz import timezone
from datetime import datetime
from freezegun import freeze_time

from django.test.client import Client
from django.test import TestCase, tag
from django.urls import resolve
from django.conf import settings
from django.contrib.messages import get_messages

from aidants_connect_web.forms import MandatForm
from aidants_connect_web.views import new_mandat
from aidants_connect_web.models import Usager, Journal, Connection, Mandat
from aidants_connect_web.tests import factories

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


@tag("new_mandat")
class NewMandatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = factories.UserFactory()

    def test_new_mandat_url_triggers_new_mandat_view(self):
        found = resolve("/new_mandat/")
        self.assertEqual(found.func, new_mandat.new_mandat)

    def test_new_mandat_url_triggers_new_mandat_template(self):
        self.client.force_login(self.aidant_thierry)
        response = self.client.get("/new_mandat/")
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_badly_formated_form_triggers_original_template(self):
        self.client.force_login(self.aidant_thierry)
        data = {"perimeter": ["papiers", "logement"], "duree": "RAMDAM"}
        response = self.client.post("/new_mandat/", data=data)
        self.assertTemplateUsed(
            response, "aidants_connect_web/new_mandat/new_mandat.html"
        )

    def test_well_formated_form_triggers_redirect_to_FC(self):
        self.client.force_login(self.aidant_thierry)
        data = {"perimeter": ["papiers", "logement"], "duree": "short"}
        response = self.client.post("/new_mandat/", data=data)
        self.assertRedirects(response, "/fc_authorize/", target_status_code=302)


@tag("new_mandat")
class RecapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant_thierry = factories.UserFactory()
        self.aidant_monique = factories.UserFactory(username="monique@monique.com")

        self.test_usager = Usager.objects.create(
            given_name="Fabrice",
            family_name="MERCIER",
            sub="46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
            preferred_username="TROIS",
            birthdate="1981-07-27",
            gender="female",
            birthplace="95277",
            birthcountry="99100",
            email="test@test.com",
        )
        self.mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"], duree=365, usager=self.test_usager
        )

    def test_recap_url_triggers_the_recap_view(self):
        found = resolve("/recap/")
        self.assertEqual(found.func, new_mandat.recap)

    def test_recap_url_triggers_the_recap_template(self):
        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = self.mandat_builder.id
        session.save()

        response = self.client.get("/recap/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/new_mandat/recap.html")

    def test_post_to_recap_with_correct_data_redirects_to_dashboard(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session

        session["connection"] = self.mandat_builder.id
        session.save()

        response = self.client.post(
            "/recap/",
            data={"personal_data": True, "brief": True, "contact_method_chosen": ""},
        )
        self.assertEqual(Usager.objects.all().count(), 1)
        usager = Usager.objects.get(given_name="Fabrice")
        self.assertEqual(
            usager.sub,
            "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )
        self.assertEqual(usager.birthplace, 95277)
        self.assertRedirects(response, "/dashboard/")

        entries = Journal.objects.all().order_by("-creation_date")
        self.assertEqual(entries.count(), 3)
        self.assertEqual(entries[0].action, "create_mandat")

    def test_post_to_recap_without_usager_creates_error(self):
        self.client.force_login(self.aidant_thierry)
        mandat_builder = Connection.objects.create(
            demarches=["papiers", "logement"], duree=1
        )
        session = self.client.session
        session["connection"] = mandat_builder.id
        session.save()
        response = self.client.post(
            "/recap/",
            data={"personal_data": True, "brief": True, "contact_method_chosen": ""},
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)

    def test_updating_mandat_for_for_same_aidant(self):

        # first session : creating the mandat
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree=3
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()
        # trigger the mandat creation/update
        self.client.post(
            "/recap/",
            data={"personal_data": True, "brief": True, "preferred_contact_method": ""},
        )

        self.assertEqual(Mandat.objects.count(), 1)
        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_mandat")

        # second session : updating the mandat
        mandat_builder_2 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree=6
        )

        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()
        # trigger the mandat creation/update
        self.client.post(
            "/recap/",
            data={"personal_data": True, "brief": True, "preferred_contact_method": ""},
        )

        self.assertEqual(Mandat.objects.count(), 1)
        updated_mandat = Mandat.objects.get(
            demarche="papiers", usager=self.test_usager, aidant=self.aidant_thierry
        )
        self.assertEqual(updated_mandat.duree, 6)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "update_mandat")

    def test_not_updating_mandat_for_different_aidant(self):
        # first session : creating the mandat
        self.client.force_login(self.aidant_thierry)
        mandat_builder_1 = Connection.objects.create(
            usager=self.test_usager, demarches=["papiers"], duree=1
        )
        session = self.client.session
        session["connection"] = mandat_builder_1.id
        session.save()
        # trigger the mandat creation/update
        self.client.post(
            "/recap/",
            data={"personal_data": True, "brief": True, "preferred_contact_method": ""},
        )
        self.client.logout()

        # second session : Create same mandat with other aidant
        self.client.force_login(self.aidant_monique)
        mandat_builder_2 = Connection.objects.create(
            demarches=["papiers"], duree=6, usager=self.test_usager
        )
        session = self.client.session
        session["connection"] = mandat_builder_2.id
        session.save()

        # trigger the mandat creation/update
        self.client.post(
            "/recap/",
            data={"personal_data": True, "brief": True, "preferred_contact_method": ""},
        )

        self.assertEqual(Mandat.objects.count(), 2)
        first_mandat = Mandat.objects.get(
            demarche="papiers", usager=self.test_usager, aidant=self.aidant_thierry
        )
        self.assertEqual(first_mandat.duree, 1)

        second_mandat = Mandat.objects.get(
            demarche="papiers", usager=self.test_usager, aidant=self.aidant_monique
        )
        self.assertEqual(second_mandat.duree, 6)

        last_journal_entry = Journal.objects.last()
        self.assertEqual(last_journal_entry.action, "create_mandat")


@tag("new_mandat")
class GenerateMandatPDF(TestCase):
    def setUp(self):
        self.aidant_thierry = factories.UserFactory()
        self.client = Client()

        self.test_usager = Usager.objects.create(
            given_name="Fabrice",
            family_name="MERCIER",
            sub="46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
            preferred_username="TROIS",
            birthdate="1981-07-27",
            gender="female",
            birthplace="95277",
            birthcountry="99100",
            email="test@test.com",
        )
        self.mandat_form = MandatForm(
            data={"perimeter": ["papiers", "logement"], "duree": "short"}
        )

        Connection.objects.create(
            id=1,
            state="test_another_state",
            connection_type="FS",
            nonce="test_another_nonce",
            demarches=["papiers", "logement"],
            duree=1,
            usager=self.test_usager,
        )

    def test_generate_mandat_PDF_triggers_the_generate_mandat_PDF_view(self):
        found = resolve("/generate_mandat_pdf/")
        self.assertEqual(found.func, new_mandat.generate_mandat_pdf)

    def test_response_is_a_pdf_download(self):
        self.client.force_login(self.aidant_thierry)
        session = self.client.session
        session["connection"] = 1
        session.save()
        response = self.client.get("/generate_mandat_pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            "inline; filename='mandat_aidants_connect.pdf'",
        )

    @freeze_time(datetime(2020, 7, 18, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris")))
    def test_pdf_contains_text(self):
        self.client.force_login(self.aidant_thierry)

        session = self.client.session
        session["connection"] = 1
        session.save()

        response = self.client.get("/generate_mandat_pdf/")
        content = io.BytesIO(response.content)
        pdfReader = PyPDF2.PdfFileReader(content)
        pageObj = pdfReader.getPage(0)
        page = pageObj.extractText()
        self.assertIn("mandataire", page)
        self.assertIn("Thierry GONEAU", page)
        self.assertIn("Fabrice MERCIER", page)
        self.assertIn("Allocation", page)
        self.assertIn("1 jour", page)
        self.assertIn("HOULBEC COCHEREL", page)
        self.assertIn("COMMUNE", page)
        self.assertIn("secrétaire", page)
        # if this fails, check if info is not on second page
        self.assertIn("18 juillet 2020", page)
