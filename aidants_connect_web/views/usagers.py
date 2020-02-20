import logging

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.models import Journal


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@activity_required
def usagers_index(request):
    messages = django_messages.get_messages(request)
    aidant = request.user
    usagers = aidant.get_usagers()

    return render(
        request,
        "aidants_connect_web/usagers.html",
        {"aidant": aidant, "usagers": usagers, "messages": messages},
    )


@login_required
@activity_required
def usager_details(request, usager_id):
    messages = django_messages.get_messages(request)
    aidant = request.user

    usager = aidant.get_usager(usager_id)
    if not usager:
        django_messages.error(request, f"Cet usager est introuvable ou inaccessible.")
        return redirect("dashboard")

    active_mandats = aidant.get_active_mandats_for_usager(usager_id)
    expired_mandats = aidant.get_expired_mandats_for_usager(usager_id)

    return render(
        request,
        "aidants_connect_web/usager_details.html",
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
def usagers_mandats_cancel_confirm(request, usager_id, mandat_id):
    aidant = request.user

    usager = aidant.get_usager(usager_id)
    if not usager:
        django_messages.error(request, "Cet usager est introuvable ou inaccessible.")
        return redirect("dashboard")

    mandat = usager.get_mandat(mandat_id)
    if not mandat:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("dashboard")

    if request.method == "POST":

        if mandat.is_expired:
            django_messages.error(request, "Le mandat est déjà expiré")
            return redirect("dashboard")

        form = request.POST
        if form:
            mandat.expiration_date = timezone.now()
            mandat.save(update_fields=["expiration_date"])

            Journal.objects.mandat_cancel(mandat)

            django_messages.success(request, "Le mandat a été révoqué avec succès !")
            return redirect("usager_details", usager_id=usager.id)

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

    return render(
        request,
        "aidants_connect_web/usagers_mandats_cancel_confirm.html",
        {"aidant": aidant, "usager": usager, "mandat": mandat},
    )
