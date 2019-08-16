import logging
from django.utils import formats
from datetime import date
from secrets import token_urlsafe
from weasyprint import HTML

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError
from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages
from django.template.loader import render_to_string

from aidants_connect_web.models import Mandat, Usager
from aidants_connect_web.forms import MandatForm


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def humanize_demarche_names(machine_names: list) -> list:
    """
    >>> humanize_demarche_names(['argent'])
    ["ARGENT: Crédit immobilier, Impôts, Consommation, Livret A, Assurance, "
            "Surendettement…"]
    :param machine_names:
    :return: list of human names and description
    """
    demarches_list = settings.DEMARCHES
    return [
        f"{demarches_list[machine_name]['titre'].upper()}: "
        f"{demarches_list[machine_name]['description']}"
        for machine_name in machine_names
    ]


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request, "aidants_connect_web/home_page.html", {"random_string": random_string}
    )


@login_required
def logout_page(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def dashboard(request):
    messages = get_messages(request)
    return render(request, "aidants_connect_web/dashboard.html", {"messages": messages})


@login_required
def mandats(request):
    messages = get_messages(request)
    aidant = request.user
    mandats = Mandat.objects.all().filter(aidant=aidant).order_by("creation_date")

    for mandat in mandats:
        mandat.perimeter_names = humanize_demarche_names(mandat.perimeter)
    # todo change the "mois" in "jours"
    return render(
        request,
        "aidants_connect_web/mandats.html",
        {"aidant": aidant, "mandats": mandats, "messages": messages},
    )


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
            request.session["mandat"] = form.cleaned_data
            return redirect("fc_authorize")
        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/new_mandat.html",
                {"aidant": aidant, "form": form},
            )


@login_required
def recap(request):
    aidant = request.user
    # TODO check if user already exists via sub

    usager_data = request.session.get("usager")

    usager = Usager(
        given_name=usager_data.get("given_name"),
        family_name=usager_data.get("family_name"),
        birthdate=usager_data.get("birthdate"),
        gender=usager_data.get("gender"),
        birthplace=usager_data.get("birthplace"),
        birthcountry=usager_data.get("birthcountry"),
        sub=usager_data.get("sub"),
    )

    mandat = request.session.get("mandat")

    if request.method == "GET":
        demarches = humanize_demarche_names(mandat["perimeter"])
        duration = "1 jour" if mandat["duration"] == "short" else "1 an"

        return render(
            request,
            "aidants_connect_web/new_mandat/recap.html",
            {
                "aidant": aidant,
                "usager": usager,
                "demarches": demarches,
                "duration": duration,
            },
        )

    else:
        form = request.POST
        if form.get("personal_data") and form.get("brief"):
            try:
                # if created is missing, the returned usager is not an instance
                # of the model
                usager, created = Usager.objects.get_or_create(
                    sub=usager.sub,
                    defaults={
                        "given_name": usager.given_name,
                        "family_name": usager.family_name,
                        "birthdate": usager.birthdate,
                        "gender": usager.gender,
                        "birthplace": usager.birthplace,
                        "birthcountry": usager.birthcountry,
                    },
                )
            except IntegrityError as e:
                log.error("Error happened in Recap")
                log.error(e)
                messages.error(request, f"The FranceConnect ID is not complete : {e}")
                return redirect("dashboard")
            duration_in_days = 1 if mandat["duration"] == "short" else 365
            Mandat.objects.create(
                aidant=aidant,
                usager=usager,
                perimeter=mandat["perimeter"],
                duration=duration_in_days,
            )

            messages.success(request, "Le mandat a été créé avec succès !")

            return redirect("dashboard")

        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/recap.html",
                {
                    "aidant": aidant,
                    "usager": usager,
                    "demarche": demarches,
                    "duration": mandat["duration"],
                    "error": "Vous devez accepter les conditions du mandat.",
                },
            )


@login_required
def generate_mandat_pdf(request):
    aidant = request.user
    usager = request.session["usager"]
    mandat = request.session["mandat"]
    demarches = mandat["perimeter"]
    duration = "1 jour" if mandat["duration"] == "short" else "1 an"
    html_string = render_to_string(
        "aidants_connect_web/new_mandat/pdf_mandat.html",
        {
            "usager": f"{usager['given_name']} {usager['family_name']}",
            "aidant": f"{aidant.first_name} {aidant.last_name.upper()}",
            "profession": aidant.profession,
            "organisme": aidant.organisme,
            "lieu": aidant.ville,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": humanize_demarche_names(demarches),
            "duree": duration,
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
