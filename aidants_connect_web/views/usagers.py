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
        django_messages.error(request, "Cet usager est introuvable ou inaccessible.")
        return redirect("dashboard")

    active_autorisations = aidant.get_active_autorisations_for_usager(usager_id)
    inactive_autorisations = aidant.get_inactive_autorisations_for_usager(usager_id)

    return render(
        request,
        "aidants_connect_web/usager_details.html",
        {
            "aidant": aidant,
            "usager": usager,
            "active_mandats": active_autorisations,
            "inactive_mandats": inactive_autorisations,
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

    autorisation = usager.get_autorisation(mandat_id)
    if not autorisation:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("dashboard")

    if request.method == "POST":

        if autorisation.is_revoked:
            django_messages.error(request, "Le mandat a été révoqué")
            return redirect("dashboard")

        if autorisation.is_expired:
            django_messages.error(request, "Le mandat est déjà expiré")
            return redirect("dashboard")

        form = request.POST
        if form:
            autorisation.revocation_date = timezone.now()
            autorisation.save(update_fields=["revocation_date"])

            Journal.objects.autorisation_cancel(autorisation, aidant)

            django_messages.success(request, "Le mandat a été révoqué avec succès !")
            return redirect("usager_details", usager_id=usager.id)

        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/usagers_mandats_cancel_confirm.html",
                {
                    "aidant": aidant,
                    "usager": usager,
                    "mandat": autorisation,
                    "error": "Erreur lors de l'annulation du mandat.",
                },
            )

    return render(
        request,
        "aidants_connect_web/usagers_mandats_cancel_confirm.html",
        {"aidant": aidant, "usager": usager, "mandat": autorisation},
    )
