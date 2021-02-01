import logging

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.models import Mandat, Journal


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@activity_required
def usagers_index(request):
    aidant = request.user
    usagers = aidant.get_usagers()

    return render(
        request,
        "aidants_connect_web/usagers.html",
        {"aidant": aidant, "usagers": usagers},
    )


@login_required
@activity_required
def usager_details(request, usager_id):
    aidant = request.user

    usager = aidant.get_usager(usager_id)
    if not usager:
        django_messages.error(request, "Cet usager est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")

    active_mandats = (
        Mandat.objects.prefetch_related("autorisations")
        .filter(organisation=aidant.organisation, usager=usager)
        .active()
    )
    inactive_mandats = (
        Mandat.objects.prefetch_related("autorisations")
        .filter(organisation=aidant.organisation, usager=usager)
        .inactive()
    )

    return render(
        request,
        "aidants_connect_web/usager_details.html",
        {
            "aidant": aidant,
            "usager": usager,
            "active_mandats": active_mandats,
            "inactive_mandats": inactive_mandats,
        },
    )


@login_required
@activity_required
def confirm_autorisation_cancelation(request, usager_id, autorisation_id):
    aidant = request.user

    usager = aidant.get_usager(usager_id)
    if not usager:
        django_messages.error(request, "Cet usager est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")

    autorisation = usager.get_autorisation(autorisation_id)

    if not autorisation:
        django_messages.error(
            request, "Cette autorisation est introuvable ou inaccessible."
        )
        return redirect("espace_aidant_home")
    if autorisation.is_revoked:
        django_messages.error(request, "L'autorisation a été révoquée")
        return redirect("espace_aidant_home")
    if autorisation.is_expired:
        django_messages.error(request, "L'autorisation a déjà expiré")
        return redirect("espace_aidant_home")

    if request.method == "POST":
        form = request.POST

        if form:
            autorisation.revocation_date = timezone.now()
            autorisation.save(update_fields=["revocation_date"])

            Journal.log_autorisation_cancel(autorisation, aidant)

            django_messages.success(
                request, "L'autorisation a été révoquée avec succès !"
            )
            return redirect("usager_details", usager_id=usager.id)

    return render(
        request,
        "aidants_connect_web/confirm_autorisation_cancelation.html",
        {"aidant": aidant, "usager": usager, "autorisation": autorisation},
    )
