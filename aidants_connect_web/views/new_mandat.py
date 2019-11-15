import logging
from django.utils import formats
from datetime import date
from weasyprint import HTML

from django.db import IntegrityError

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from django.contrib import messages
from django.template.loader import render_to_string

from aidants_connect_web.models import Mandat, Connection
from aidants_connect_web.forms import MandatForm, RecapForm
from aidants_connect_web.views.service import humanize_demarche_names


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
def new_mandat(request):
    aidant = request.user
    form = MandatForm()

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/new_mandat/new_mandat.html",
            {"aidant": aidant, "form": form},
        )

    else:
        form = MandatForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            duree = 1 if data["duree"] == "short" else 365
            connection = Connection.objects.create(
                demarches=data["perimeter"], duree=duree
            )
            request.session["connection"] = connection.pk
            return redirect("fc_authorize")
        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/new_mandat.html",
                {"aidant": aidant, "form": form},
            )


@login_required
def recap(request):

    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    duree = "1 jour" if connection.duree == 1 else "1 an"
    demarches_description = [
        humanize_demarche_names(demarche) for demarche in connection.demarches
    ]
    form = RecapForm()
    if request.method == "GET":

        return render(
            request,
            "aidants_connect_web/new_mandat/recap.html",
            {
                "form": form,
                "aidant": aidant,
                "usager": usager,
                "demarches": demarches_description,
                "duree": duree,
                "contact_method_list": settings.CONTACT_METHOD,
            },
        )

    else:
        form = RecapForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            form_chosen_method = data["preferred_contact_method"]
            if form_chosen_method:
                if (form_chosen_method in ["sms", "phone"]) and data["contact_phone"]:
                    usager.contact_phone = data["contact_phone"]
                elif form_chosen_method == "email" and data["contact_email"]:
                    usager.contact_email = data["contact_email"]
                elif form_chosen_method == "address" and data["contact_address"]:
                    usager.contact_address = data["contact_address"]
                else:
                    form_chosen_method = ""
                usager.preferred_contact_method = form_chosen_method

                usager.save()

            for demarche in connection.demarches:
                try:
                    Mandat.objects.update_or_create(
                        aidant=aidant,
                        usager=usager,
                        demarche=demarche,
                        defaults={
                            "duree": connection.duree,
                            "modified_by_access_token": connection.access_token,
                        },
                    )

                except IntegrityError as e:
                    log.error("Error happened in Recap")
                    log.error(e)
                    messages.error(request, f"No Usager was given : {e}")
                    return redirect("dashboard")

            messages.success(request, "Le mandat a été créé avec succès !")

            return redirect("dashboard")

        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/recap.html",
                {
                    "aidant": aidant,
                    "usager": usager,
                    "demarche": demarches_description,
                    "duree": duree,
                    "contact_method_list": settings.CONTACT_METHOD,
                    "form": form,
                },
            )


@login_required
def generate_mandat_pdf(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user

    usager = connection.usager
    demarches = connection.demarches

    duree = "1 jour" if connection.duree == 1 else "1 an"

    html_string = render_to_string(
        "aidants_connect_web/new_mandat/pdf_mandat.html",
        {
            "usager": f"{usager.given_name} {usager.family_name}",
            "aidant": f"{aidant.first_name} {aidant.last_name.upper()}",
            "profession": aidant.profession,
            "organisme": aidant.organisme,
            "lieu": aidant.ville,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
        },
    )

    html = HTML(string=html_string)
    html.write_pdf(target="/tmp/mandat_aidants_connect.pdf")

    fs = FileSystemStorage("/tmp")
    with fs.open("mandat_aidants_connect.pdf") as pdf:
        response = HttpResponse(pdf, content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = "inline; filename='mandat_aidants_connect.pdf'"
        return response
