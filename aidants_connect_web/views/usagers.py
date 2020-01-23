import logging

from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from aidants_connect_web.models import (
    Usager,
    Mandat
)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@activity_required
def usagers_index(request):
    request_messages = messages.get_messages(request)
    aidant = request.user
    # TODO: understand why there is a bug if 'usagers' as variable
    aidant_usagers = aidant.get_usagers()

    return render(
        request,
        "aidants_connect_web/usagers.html",
        {
            "aidant": aidant,
            "aidant_usagers": aidant_usagers,
            "messages": request_messages
        },
    )


@login_required
@activity_required
def usagers_details(request, usager_id):
    request_messages = messages.get_messages(request)
    aidant = request.user
    usager = Usager.objects.get(pk=usager_id)
    active_mandats = aidant.get_active_mandats_for_usager(usager_id)
    expired_mandats = aidant.get_expired_mandats_for_usager(usager_id)

    return render(
        request,
        "aidants_connect_web/usagers_details.html",
        {
            "aidant": aidant,
            "usager": usager,
            "active_mandats": active_mandats,
            "expired_mandats": expired_mandats,
            "messages": request_messages
        },
    )


@login_required
def usagers_mandats_cancel_confirm(request, usager_id, mandat_id):
    aidant = request.user
    usager = Usager.objects.get(pk=usager_id)
    mandat = Mandat.objects.get(pk=mandat_id)

    if request.method == "GET":

        return render(
            request,
            "aidants_connect_web/usagers_mandats_cancel_confirm.html",
            {
                "aidant": aidant,
                "usager": usager,
                "mandat": mandat,
            },
        )

    else:
        form = request.POST

        if form:
            try:
                mandat.expiration_date = timezone.now()
                mandat.save()

                messages.success(request, "Le mandat a été annulé avec succès !")

                return redirect('usagers_details', usager_id=usager.id)

            except IntegrityError as e:
                log.error("Error happened in Cancel Mandat")
                log.error(e)
                messages.error(request, f"No Usager was given : {e}")
                return redirect("dashboard")

        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/usagers_mandats_cancel_confirm.html",
                {
                    "aidant": aidant,
                    "usager": usager,
                    "mandat": mandat,
                    "error": "Erreur lors de l'annulation du mandat.",
                },
            )
