import io
import PyPDF2
from pytz import timezone
from datetime import datetime
from freezegun import freeze_time

from django.test.client import Client
from django.test import TestCase
from django.urls import resolve
from django.conf import settings
from django.contrib.messages import get_messages

from aidants_connect_web.forms import MandatForm
from aidants_connect_web.views import new_mandat
from aidants_connect_web.models import Aidant, Usager, Journal

fc_callback_url = settings.FC_AS_FI_CALLBACK_URL


class RecapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = Aidant.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )

    def test_recap_url_triggers_the_recap_view(self):
        found = resolve("/recap/")
        self.assertEqual(found.func, new_mandat.recap)

    def test_recap_url_triggers_the_recap_template(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "sub": "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "female",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        mandat_form = MandatForm(
            data={"perimeter": ["papiers", "logement"], "duration": "long"}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()

        response = self.client.get("/recap/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "aidants_connect_web/new_mandat/recap.html")
        self.assertEqual(Usager.objects.all().count(), 0)

    def test_post_to_recap_with_correct_data_redirects_to_dashboard(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "sub": "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "F",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        mandat_form = MandatForm(
            data={"perimeter": ["papiers", "logement"], "duration": "short"}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()

        response = self.client.post(
            "/recap/", data={"personal_data": True, "brief": True}
        )
        self.assertEqual(Usager.objects.all().count(), 1)
        usager = Usager.objects.get(given_name="Fabrice")
        self.assertEqual(
            usager.sub,
            "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        )
        self.assertEqual(usager.birthplace, 95277)
        self.assertRedirects(response, "/dashboard/")

        entries = Journal.objects.all()
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries[0].action, "create_mandat")

    def test_post_to_recap_without_sub_creates_error(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "F",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        mandat_form = MandatForm(
            data={"perimeter": ["papiers", "logement"], "duration": "long"}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()
        response = self.client.post(
            "/recap/", data={"personal_data": True, "brief": True}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)

    def test_post_to_recap_checks_existing_sub_and_doesnt_update_info(self):
        self.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate="1969-12-15",
            gender="female",
            birthplace="70447",
            birthcountry="99100",
            sub="123",
            email="User@user.domain",
            creation_date="2019-08-05T15:49:13.972Z",
        )
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = {
            "given_name": "Fabrice",
            "family_name": "Mercier",
            "sub": "123",
            "preferred_username": "TROIS",
            "birthdate": "1981-07-27",
            "gender": "female",
            "birthplace": "95277",
            "birthcountry": "99100",
            "email": "test@test.com",
        }
        creation_date = self.usager.creation_date
        mandat_form = MandatForm(
            data={"perimeter": ["papiers", "logement"], "duration": "short"}
        )
        mandat_form.is_valid()
        session["mandat"] = mandat_form.cleaned_data
        session.save()
        self.client.post("/recap/", data={"personal_data": True, "brief": True})
        self.assertEqual(Usager.objects.all().count(), 1)
        self.assertEqual(Usager.objects.first().given_name, "Joséphine")
        self.assertEqual(Usager.objects.filter(sub="123").count(), 1)
        self.assertEqual(Usager.objects.filter(creation_date=creation_date).count(), 1)


class GenerateMandatPDF(TestCase):
    def setUp(self):
        self.client = Client()
        self.aidant = Aidant.objects.create_user(
            "Thierry", "thierry@thierry.com", "motdepassedethierry"
        )
        self.aidant.last_name = "Goneau"
        self.aidant.first_name = "Thierry"
        self.aidant.profession = "secrétaire"
        self.aidant.organisme = "COMMUNE DE HOULBEC COCHEREL"
        self.aidant.ville = "HOULBEC COCHEREL"
        self.aidant.save()

    def test_generate_mandat_PDF_triggers_the_generate_mandat_PDF_view(self):
        found = resolve("/generate_mandat_pdf/")
        self.assertEqual(found.func, new_mandat.generate_mandat_pdf)

    test_usager = {
        "given_name": "Fabrice",
        "family_name": "MERCIER",
        "sub": "46df505a40508b9fa620767c73dc1d7ad8c30f66fa6ae5ae963bf9cccc885e8dv1",
        "preferred_username": "TROIS",
        "birthdate": "1981-07-27",
        "gender": "female",
        "birthplace": "95277",
        "birthcountry": "99100",
        "email": "test@test.com",
    }

    test_mandat = {"perimeter": ["famille"], "duration": "short"}

    def test_response_is_a_pdf_download(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = self.test_usager
        session["mandat"] = self.test_mandat
        session.save()
        response = self.client.get("/generate_mandat_pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            "inline; filename='mandat_aidants_connect.pdf'",
        )

    @freeze_time(datetime(2020, 7, 18, 3, 20, 34, 0, tzinfo=timezone("Europe/Paris")))
    def test_pdf_contains_text(self):
        self.client.login(username="Thierry", password="motdepassedethierry")
        session = self.client.session
        session["usager"] = self.test_usager
        session["mandat"] = self.test_mandat
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
