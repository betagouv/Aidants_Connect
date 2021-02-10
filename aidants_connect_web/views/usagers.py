import logging

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.models import Mandat, Journal, Autorisation


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
    try:
        autorisation = aidant.get_active_autorisations_for_usager(usager_id).get(
            pk=autorisation_id
        )
    except Autorisation.DoesNotExist:
        django_messages.error(
            request, "Cette autorisation est introuvable ou inaccessible."
        )
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
            return redirect("usager_details", usager_id=usager_id)

    return render(
        request,
        "aidants_connect_web/confirm_autorisation_cancelation.html",
        {
            "aidant": aidant,
            "usager": aidant.get_usager(usager_id),
            "autorisation": autorisation,
        },
    )


@login_required
@activity_required
def confirm_mandat_cancelation(request, mandat_id):
    aidant = request.user
    try:
        mandat = Mandat.objects.get(pk=mandat_id, organisation=aidant.organisation)
    except Mandat.DoesNotExist:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")
    if mandat.is_active:
        usager = mandat.usager
        remaining_autorisations = (
            mandat.autorisations.all()
            .filter(revocation_date=None)
            .values_list("demarche", flat=True)
        )

        if request.method == "POST":
            if request.POST:
                autorisation_in_mandat = Autorisation.objects.filter(mandat=mandat)
                for autorisation in autorisation_in_mandat:
                    if not autorisation.revocation_date:
                        autorisation.revocation_date = (
                            autorisation.revocation_date
                        ) = timezone.now()
                        autorisation.save(update_fields=["revocation_date"])

                return redirect("usager_details", usager_id=usager.id)
            else:
                return render(
                    request,
                    "aidants_connect_web/confirm_mandat_cancellation.html",
                    {
                        "aidant": aidant,
                        "usager_name": usager.get_full_name(),
                        "usager_id": usager.id,
                        "mandat": mandat,
                        "remaining_autorisations": remaining_autorisations,
                        "error": """
                            Une erreur s'est produite lors de la révocation du mandat
                            """,
                    },
                )

    return render(
        request,
        "aidants_connect_web/confirm_mandat_cancellation.html",
        {
            "aidant": aidant,
            "usager_name": usager.get_full_name(),
            "usager_id": usager.id,
            "mandat": mandat,
            "remaining_autorisations": remaining_autorisations,
        },
    )
