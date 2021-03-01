import logging
from collections import OrderedDict

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Concat
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.timezone import timedelta, now

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.models import Mandat, Journal, Autorisation

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def _get_mandats_for_usagers_index(aidant):
    return (
        Mandat.objects.prefetch_related("autorisations")
        .filter(organisation=aidant.organisation)
        .annotate(
            for_ordering=Concat("usager__preferred_username", "usager__family_name")
        )
        .order_by("for_ordering", "expiration_date")
    )


def _get_usagers_dict_from_mandats(mandats):
    usagers = OrderedDict()
    usagers_without_mandats = set()
    delta = settings.MANDAT_EXPIRED_SOON
    for mandat in mandats:
        if mandat.usager not in usagers:
            usagers[mandat.usager] = list()
        expired = mandat.expiration_date if mandat.expiration_date < now() else False
        if expired:
            usagers_without_mandats.add(mandat.usager)
            continue

        expired_soon = (
            mandat.expiration_date
            if mandat.expiration_date - timedelta(days=delta) < now()
            else False
        )

        for autorisation in mandat.autorisations.all().order_by("pk"):
            if autorisation.revocation_date is None:
                if mandat.usager in usagers_without_mandats:
                    usagers_without_mandats.remove(mandat.usager)

                usagers[mandat.usager].append((autorisation.demarche, expired_soon))
            elif not usagers[mandat.usager]:
                usagers_without_mandats.add(mandat.usager)

    for usager in usagers_without_mandats:
        usagers[usager] = [("Aucun mandat valide", None)]
    return usagers


@login_required
@activity_required
def usagers_index(request):
    aidant = request.user
    mandats = _get_mandats_for_usagers_index(aidant)
    usagers = _get_usagers_dict_from_mandats(mandats)

    return render(
        request,
        "aidants_connect_web/usagers.html",
        {
            "aidant": aidant,
            "usagers": usagers,
        },
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
    usager = mandat.usager
    if mandat.is_active:
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
                        Journal.log_autorisation_cancel(autorisation, aidant)
                Journal.log_mandat_cancel(mandat, aidant)
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
            "remaining_autorisations": [],
        },
    )
