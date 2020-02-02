import logging
from datetime import date, timedelta

from django.db import IntegrityError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone, formats

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.forms import MandatForm, RecapMandatForm
from aidants_connect_web.models import Mandat, Connection
from aidants_connect_web.views.service import humanize_demarche_names

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@activity_required
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
                demarches=data["demarche"], duree=duree
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
def new_mandat_recap(request):

    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    duree = "1 jour" if connection.duree == 1 else "1 an"
    demarches_description = [
        humanize_demarche_names(demarche) for demarche in connection.demarches
    ]
    if request.method == "GET":
        form = RecapMandatForm(aidant)
        return render(
            request,
            "aidants_connect_web/new_mandat/new_mandat_recap.html",
            {
                "aidant": aidant,
                "usager": usager,
                "demarches": demarches_description,
                "duree": duree,
                "form": form,
            },
        )

    else:
        form = RecapMandatForm(aidant=aidant, data=request.POST)
        if form.is_valid():
            # The loop below creates one Mandat object per Démarche selected in the form
            for demarche in connection.demarches:
                try:
                    Mandat.objects.update_or_create(
                        aidant=aidant,
                        usager=usager,
                        demarche=demarche,
                        defaults={
                            "expiration_date": timezone.now()
                            + timedelta(days=connection.duree),
                            "last_mandat_renewal_date": timezone.now(),
                            "last_mandat_renewal_token": connection.access_token,
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
                "aidants_connect_web/new_mandat/new_mandat_recap.html",
                {
                    "aidant": aidant,
                    "usager": usager,
                    "demarche": demarches_description,
                    "duree": duree,
                    "form": form,
                    "error": form.errors,
                },
            )


@login_required
def new_mandat_preview(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user

    usager = connection.usager
    demarches = connection.demarches

    duree = "1 jour" if connection.duree == 1 else "1 an"

    return render(
        request,
        "aidants_connect_web/new_mandat/new_mandat_preview.html",
        {
            "usager": f"{usager.given_name} {usager.family_name}",
            "aidant": f"{aidant.first_name} {aidant.last_name.upper()}",
            "profession": aidant.profession,
            "organisation": aidant.organisation.name,
            "lieu": aidant.organisation.address,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
        },
    )
