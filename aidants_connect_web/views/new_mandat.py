from datetime import date, timedelta
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.utils import timezone, formats
from django.http import HttpResponse
from django.conf import settings

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.forms import MandatForm, RecapMandatForm
from aidants_connect_web.models import Mandat, Connection, Journal
from aidants_connect_web.views.service import humanize_demarche_names
from aidants_connect_web.utilities import (
    generate_file_sha256_hash,
    generate_sha256_hash,
    generate_qrcode_png,
)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def generate_mandat_print_hash(aidant, usager, demarches, expiration_date):
    demarches.sort()
    mandat_print_data = {
        "aidant_id": aidant.id,
        "creation_date": date.today().isoformat(),
        "demarches_list": ",".join(demarches),
        "expiration_date": expiration_date.date().isoformat(),
        "organisation_id": aidant.organisation.id,
        "template_hash": generate_file_sha256_hash(settings.MANDAT_TEMPLATE_PATH),
        "usager_sub": usager.sub,
    }
    sorted_mandat_print_data = dict(sorted(mandat_print_data.items()))
    mandat_print_string = ",".join(
        str(x) for x in list(sorted_mandat_print_data.values())
    )
    mandat_print_string_with_salt = mandat_print_string + settings.MANDAT_PRINT_SALT
    return generate_sha256_hash(mandat_print_string_with_salt.encode("utf-8"))


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
                aidant=request.user, demarches=data["demarche"], duree=duree
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
@activity_required
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
            mandat_expiration_date = timezone.now() + timedelta(days=connection.duree)

            try:
                # Add a Journal 'print_mandat' action
                connection.demarches.sort()
                Journal.objects.mandat_print(
                    aidant=aidant,
                    usager=usager,
                    demarches=connection.demarches,
                    duree=connection.duree,
                    mandat_print_hash=generate_mandat_print_hash(
                        aidant, usager, connection.demarches, mandat_expiration_date
                    ),
                )

                # The loop below creates one Mandat object per Démarche in the form
                for demarche in connection.demarches:
                    Mandat.objects.update_or_create(
                        aidant=aidant,
                        usager=usager,
                        demarche=demarche,
                        defaults={
                            "expiration_date": mandat_expiration_date,
                            "last_mandat_renewal_date": timezone.now(),
                            "last_mandat_renewal_token": connection.access_token,
                        },
                    )

            except AttributeError as error:
                log.error("Error happened in Recap")
                log.error(error)
                messages.error(request, f"Error with Usager attribute : {error}")
                return redirect("dashboard")

            except IntegrityError as error:
                log.error("Error happened in Recap")
                log.error(error)
                messages.error(request, f"No Usager was given : {error}")
                return redirect("dashboard")

            return redirect("new_mandat_success")

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
                },
            )


@login_required
@activity_required
def new_mandat_success(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager

    return render(
        request,
        "aidants_connect_web/new_mandat/new_mandat_success.html",
        {"aidant": aidant, "usager": usager},
    )


@login_required
@activity_required
def mandat_preview_projet(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    duree = "1 jour" if connection.duree == 1 else "1 an"

    return render(
        request,
        "aidants_connect_web/mandat_preview.html",
        {
            "usager": usager,
            "aidant": aidant,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
        },
    )


@login_required
@activity_required
def mandat_preview_final(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    duree = "1 jour" if connection.duree == 1 else "1 an"

    return render(
        request,
        "aidants_connect_web/mandat_preview.html",
        {
            "usager": usager,
            "aidant": aidant,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
            "final": True,
        },
    )


@login_required
@activity_required
def mandat_preview_final_qrcode(request):
    aidant = request.user

    journal_print_mandat = aidant.get_journal_of_last_print_mandat()
    journal_print_mandat_qrcode_png = generate_qrcode_png(
        journal_print_mandat.mandat_print_hash
    )

    return HttpResponse(journal_print_mandat_qrcode_png, "image/png")
