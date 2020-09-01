from datetime import date, timedelta
import logging

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.utils import timezone, formats
from django.http import HttpResponse
from django.conf import settings

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.forms import MandatForm, RecapMandatForm
from aidants_connect_web.models import Autorisation, Connection, Journal, Mandat
from aidants_connect_web.views.service import humanize_demarche_names
from aidants_connect_web.utilities import (
    generate_file_sha256_hash,
    generate_sha256_hash,
    generate_qrcode_png,
)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def generate_attestation_hash(aidant, usager, demarches, expiration_date):
    demarches.sort()
    attestation_data = {
        "aidant_id": aidant.id,
        "creation_date": date.today().isoformat(),
        "demarches_list": ",".join(demarches),
        "expiration_date": expiration_date.date().isoformat(),
        "organisation_id": aidant.organisation.id,
        "template_hash": generate_file_sha256_hash(settings.MANDAT_TEMPLATE_PATH),
        "usager_sub": usager.sub,
    }
    sorted_attestation_data = dict(sorted(attestation_data.items()))
    attestation_string = ";".join(
        str(x) for x in list(sorted_attestation_data.values())
    )
    attestation_string_with_salt = attestation_string + settings.ATTESTATION_SALT
    return generate_sha256_hash(attestation_string_with_salt.encode("utf-8"))


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
            connection = Connection.objects.create(
                aidant=request.user,
                demarches=data["demarche"],
                duree_keyword=data["duree"],
                mandat_is_remote=data["is_remote"],
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
    demarches_description = [
        humanize_demarche_names(demarche) for demarche in connection.demarches
    ]
    duree = connection.get_duree_keyword_display()
    is_remote = connection.mandat_is_remote

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
                "is_remote": is_remote,
                "form": form,
            },
        )

    else:
        form = RecapMandatForm(aidant=aidant, data=request.POST)

        if form.is_valid():
            now = timezone.now()
            expiration_date = {
                "SHORT": now + timedelta(days=1),
                "LONG": now + timedelta(days=365),
                "EUS_03_20": settings.ETAT_URGENCE_2020_LAST_DAY,
            }
            mandat_expiration_date = expiration_date.get(connection.duree_keyword)
            days_before_expiration_date = {
                "SHORT": 1,
                "LONG": 365,
                "EUS_03_20": 1 + (settings.ETAT_URGENCE_2020_LAST_DAY - now).days,
            }
            mandat_duree = days_before_expiration_date.get(connection.duree_keyword)

            try:
                # Add a Journal 'create_attestation' action
                connection.demarches.sort()
                Journal.log_attestation_creation(
                    aidant=aidant,
                    usager=usager,
                    demarches=connection.demarches,
                    duree=mandat_duree,
                    is_remote_mandat=connection.mandat_is_remote,
                    access_token=connection.access_token,
                    attestation_hash=generate_attestation_hash(
                        aidant, usager, connection.demarches, mandat_expiration_date
                    ),
                )

                # Create a mandat
                mandat = Mandat.objects.create(
                    organisation=aidant.organisation,
                    usager=usager,
                    duree_keyword=connection.duree_keyword,
                    expiration_date=mandat_expiration_date,
                    is_remote=connection.mandat_is_remote,
                )

                # This loop creates one `autorisation` object per `démarche` in the form
                for demarche in connection.demarches:
                    # Revoke existing demarche autorisation(s)
                    similar_active_autorisations = Autorisation.objects.active().filter(
                        mandat__organisation=aidant.organisation,
                        mandat__usager=usager,
                        demarche=demarche,
                    )
                    for similar_active_autorisation in similar_active_autorisations:
                        similar_active_autorisation.revoke(
                            aidant=aidant, revocation_date=now
                        )

                    # Create new demarche autorisation
                    autorisation = Autorisation.objects.create(
                        mandat=mandat,
                        demarche=demarche,
                        last_renewal_token=connection.access_token,
                    )
                    Journal.log_autorisation_creation(autorisation, aidant)

            except AttributeError as error:
                log.error("Error happened in Recap")
                log.error(error)
                django_messages.error(request, f"Error with Usager attribute : {error}")
                return redirect("espace_aidant_home")

            except IntegrityError as error:
                log.error("Error happened in Recap")
                log.error(error)
                django_messages.error(request, f"No Usager was given : {error}")
                return redirect("espace_aidant_home")

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
def attestation_projet(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    # Django magic :
    # https://docs.djangoproject.com/en/3.0/ref/models/instances/#django.db.models.Model.get_FOO_display
    duree = connection.get_duree_keyword_display()

    return render(
        request,
        "aidants_connect_web/attestation.html",
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
def attestation_final(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    # Django magic :
    # https://docs.djangoproject.com/en/3.0/ref/models/instances/#django.db.models.Model.get_FOO_display
    duree = connection.get_duree_keyword_display()

    return render(
        request,
        "aidants_connect_web/attestation.html",
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
def attestation_qrcode(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user

    journal_create_attestation = aidant.get_journal_create_attestation(
        connection.access_token
    )
    journal_create_attestation_qrcode_png = generate_qrcode_png(
        journal_create_attestation.attestation_hash
    )

    return HttpResponse(journal_create_attestation_qrcode_png, "image/png")
