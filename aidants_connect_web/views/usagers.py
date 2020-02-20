import logging

from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages

from aidants_connect_web.models import Usager, Mandat, Journal
from aidants_connect_web.decorators import (
    activity_required,
    check_mandat_usager,
    check_mandat_aidant,
    check_mandat_is_expired,
    check_mandat_is_not_expired,
    check_mandat_is_cancelled,
)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@activity_required
def usagers_index(request):
    messages = django_messages.get_messages(request)
    aidant = request.user
    # TODO: understand why there is a bug if 'usagers' as variable
    aidant_usagers = aidant.get_usagers()

    return render(
        request,
        "aidants_connect_web/usagers.html",
        {"aidant": aidant, "aidant_usagers": aidant_usagers, "messages": messages},
    )


@login_required
@activity_required
def usagers_details(request, usager_id):
    messages = django_messages.get_messages(request)
    aidant = request.user
    usager = get_object_or_404(Usager, pk=usager_id)
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
            "messages": messages,
        },
    )


@login_required
@activity_required
@check_mandat_usager
@check_mandat_aidant
@check_mandat_is_not_expired
def usagers_mandats_cancel_confirm(request, usager_id, mandat_id):
    aidant = request.user
    usager = get_object_or_404(Usager, pk=usager_id)
    mandat = get_object_or_404(Mandat, pk=mandat_id)

    if request.method == "GET":

        return render(
            request,
            "aidants_connect_web/usagers_mandats_cancel_confirm.html",
            {"aidant": aidant, "usager": usager, "mandat": mandat},
        )

    else:
        form = request.POST

        if form:
            mandat.expiration_date = timezone.now()
            mandat.save(update_fields=["expiration_date"])

            Journal.objects.mandat_cancel(mandat)

            return redirect(
                "usagers_mandats_cancel_success",
                usager_id=usager.id,
                mandat_id=mandat.id,
            )

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


@login_required
@activity_required
@check_mandat_usager
@check_mandat_aidant
@check_mandat_is_expired
@check_mandat_is_cancelled
def usagers_mandats_cancel_success(request, usager_id, mandat_id):
    aidant = request.user
    usager = get_object_or_404(Usager, pk=usager_id)
    mandat = get_object_or_404(Mandat, pk=mandat_id)

    return render(
        request,
        "aidants_connect_web/usagers_mandats_cancel_success.html",
        {"aidant": aidant, "usager": usager, "mandat": mandat},
    )
