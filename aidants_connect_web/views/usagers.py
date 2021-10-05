import logging
from collections import OrderedDict
from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Concat
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import timedelta, now
from django.views.decorators.http import require_http_methods

from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.models import (
    Mandat,
    Journal,
    Autorisation,
    Aidant,
    Organisation,
)
from aidants_connect_web.views.service import humanize_demarche_names


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


def _get_usagers_dict_from_mandats(mandats: Mandat) -> dict:
    """
    :return: A dict containing data about the users from input mandates with attributes:

            with_valid_mandate -> OrderedDict[Usager, list[Tuple[str, bool]]

                dictionnary associating the user with the list of its mandate's
                authorizations. Each item of the list is a tuple of two items: the
                the procedure (see aidants_connect.settings.DEMARCHES) covered by the
                authorization (see aidants_aidants_connect_web.models.Autorisation) and
                a boolean indication if the authorisation is soon to be expired.

            without_valid_mandate -> set[Usager]

                dict associating users without an active mandate with the number of
                expired mandates

            with_valid_mandate_count -> int

                count of items in ``with_valid_mandate``

            without_valid_mandate_count: int

                count of items in ``without_valid_mandate``

            total: int

                total count of both ``with_valid_mandate`` and ``without_valid_mandate``

        Example:
            $ _get_usagers_dict_from_mandats(mandates)
            {
                "with_valid_mandate": {
                    <Usager: Angela Claire Louise DUBOIS>: [
                        ("papiers", False), ("transports", False)
                    ]
                },
                "without_valid_mandate": {<Usager: Karl MARX>},
                "with_valid_mandate_count": 1,
                "without_valid_mandate_count": 1,
                "total"2
            }
    """
    usagers = OrderedDict()
    usagers_without_mandats = set()
    delta = settings.MANDAT_EXPIRED_SOON
    for mandat in mandats:
        expired = mandat.expiration_date if mandat.expiration_date < now() else False
        if expired:
            usagers_without_mandats.add(mandat.usager)
            continue

        expired_soon = (
            mandat.expiration_date
            if mandat.expiration_date - timedelta(days=delta) < now()
            else False
        )

        autorisations = (
            mandat.autorisations.filter(revocation_date=None).all().order_by("pk")
        )

        if autorisations.count() == 0:
            if mandat.usager not in usagers:
                usagers_without_mandats.add(mandat.usager)
        else:
            if mandat.usager not in usagers:
                usagers[mandat.usager] = list()
            if mandat.usager in usagers_without_mandats:
                usagers_without_mandats.remove(mandat.usager)

            for autorisation in autorisations:
                usagers[mandat.usager].append((autorisation.demarche, expired_soon))

    with_valid_mandate_count = len(usagers)
    without_valid_mandate_count = len(usagers_without_mandats)

    return {
        "with_valid_mandate": usagers,
        "without_valid_mandate": usagers_without_mandats,
        "with_valid_mandate_count": with_valid_mandate_count,
        "without_valid_mandate_count": without_valid_mandate_count,
        "total": with_valid_mandate_count + without_valid_mandate_count,
    }


@login_required
@activity_required
def usagers_index(request):
    aidant = request.user
    mandats = _get_mandats_for_usagers_index(aidant)
    usagers_dict = _get_usagers_dict_from_mandats(mandats)

    return render(
        request,
        "aidants_connect_web/usagers/usagers.html",
        {
            "aidant": aidant,
            "usagers_dict": usagers_dict,
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

            return redirect(
                "autorisation_cancelation_success",
                usager_id=usager_id,
                autorisation_id=autorisation_id,
            )

    return render(
        request,
        "aidants_connect_web/mandat_auths_cancellation/"
        "confirm_autorisation_cancelation.html",
        {
            "aidant": aidant,
            "usager": aidant.get_usager(usager_id),
            "autorisation": autorisation,
        },
    )


@login_required
@activity_required
def autorisation_cancelation_success(request, usager_id, autorisation_id):
    aidant: Aidant = request.user

    try:
        authorization = aidant.get_inactive_autorisations_for_usager(usager_id).get(
            pk=autorisation_id
        )
    except Autorisation.DoesNotExist:
        django_messages.error(
            request, "Cette autorisation est introuvable ou inaccessible."
        )
        return redirect("espace_aidant_home")

    if not authorization.is_revoked:
        django_messages.error(request, "Cette autorisation est encore active.")
        return redirect("espace_aidant_home")

    return render(
        request,
        "aidants_connect_web/mandat_auths_cancellation/"
        "authorization_cancellation_success.html",
        {
            "aidant": aidant,
            "humanized_auth": humanize_demarche_names(authorization.demarche),
            "usager": aidant.get_usager(usager_id),
            "authorization": authorization,
        },
    )


@login_required
@activity_required
def autorisation_cancelation_attestation(request, usager_id, autorisation_id):
    aidant: Aidant = request.user
    try:
        autorisation = aidant.get_inactive_autorisations_for_usager(usager_id).get(
            pk=autorisation_id
        )
    except Autorisation.DoesNotExist:
        django_messages.error(
            request, "Cette autorisation est introuvable ou inaccessible."
        )
        return redirect("espace_aidant_home")

    mandat: Mandat = autorisation.mandat

    if not autorisation.is_revoked:
        django_messages.error(request, "Cette autorisation est encore active.")
        return redirect("espace_aidant_home")

    if not autorisation.was_separately_revoked:
        return redirect("mandat_cancellation_attestation", mandat_id=mandat.id)

    user = aidant.get_usager(usager_id)

    return render(
        request,
        "aidants_connect_web/mandat_auths_cancellation/"
        "authorization_cancellation_attestation.html",
        {
            "aidant": aidant,
            "authorization": humanize_demarche_names(autorisation.demarche),
            "user": user,
            "organisation": autorisation.mandat.organisation,
            "creation_date": autorisation.mandat.creation_date.strftime(
                "%d/%m/%Y à %Hh%M"
            ),
            "revocation_date": autorisation.revocation_date.strftime(
                "%d/%m/%Y à %Hh%M"
            ),
        },
    )


@login_required
@activity_required
def confirm_mandat_cancelation(request, mandat_id):
    aidant: Aidant = request.user
    try:
        mandat = Mandat.objects.get(pk=mandat_id, organisation=aidant.organisation)
    except Mandat.DoesNotExist:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")

    usager = mandat.usager
    remaining_autorisations = []

    if mandat.is_active:
        for autorisation in mandat.autorisations.filter(revocation_date=None):
            remaining_autorisations.append(
                humanize_demarche_names(autorisation.demarche)
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
                return redirect("mandat_cancelation_success", mandat_id=mandat.id)
            else:
                return render(
                    request,
                    "aidants_connect_web/mandat_auths_cancellation/"
                    "confirm_mandat_cancellation.html",
                    {
                        "aidant": aidant,
                        "usager_name": usager.get_full_name(),
                        "usager_id": usager.id,
                        "mandat": mandat,
                        "remaining_autorisations": remaining_autorisations,
                        "error": "Une erreur s'est produite lors "
                        "de la révocation du mandat",
                    },
                )

    return render(
        request,
        "aidants_connect_web/mandat_auths_cancellation/"
        "confirm_mandat_cancellation.html",
        {
            "aidant": aidant,
            "usager_name": usager.get_full_name(),
            "usager_id": usager.id,
            "mandat": mandat,
            "remaining_autorisations": remaining_autorisations,
        },
    )


@login_required
@activity_required
def mandat_cancelation_success(request, mandat_id: int):
    aidant: Aidant = request.user
    try:
        mandate = Mandat.objects.get(pk=mandat_id, organisation=aidant.organisation)
    except Mandat.DoesNotExist:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")
    user = mandate.usager
    if mandate.is_active:
        django_messages.error(request, "Ce mandat est toujours actif.")
        return redirect("usager_details", usager_id=user.id)

    return render(
        request,
        "aidants_connect_web/mandat_auths_cancellation/"
        "mandat_cancellation_success.html",
        {
            "aidant": aidant,
            "mandat": mandate,
            "usager": user,
        },
    )


@login_required
@activity_required
def mandat_cancellation_attestation(request, mandat_id):
    organisation = request.user.organisation
    try:
        mandat = Mandat.objects.get(pk=mandat_id, organisation=organisation)
        if not mandat.was_explicitly_revoked:
            return redirect("espace_aidant_home")

    except Mandat.DoesNotExist:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")
    usager = mandat.usager

    return render(
        request,
        "aidants_connect_web/mandat_auths_cancellation/"
        "mandat_cancellation_attestation.html",
        {
            "organisation": organisation,
            "usager_name": usager.get_full_name(),
            "mandat": mandat,
            "creation_date": mandat.creation_date.strftime("%d/%m/%Y à %Hh%M"),
            "revocation_date": mandat.revocation_date.strftime("%d/%m/%Y à %Hh%M"),
        },
    )


@login_required
@activity_required
@user_is_aidant
@require_http_methods(["GET", "POST"])
def switch_main_organisation(request: HttpRequest):
    aidant: Aidant = request.user

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/espace_aidant/switch_main_organisation.html",
            {
                "aidant": aidant,
                "next_url": request.GET.get("next", ""),
                "organisations": aidant.organisations,
                "disable_change_organisation": True,
            },
        )

    organisation_id = request.POST["organisation"]

    try:
        organisation = Organisation.objects.get(pk=organisation_id)
    except Organisation.DoesNotExist:
        django_messages.error(
            request,
            f"Aucune organisation portant l'identifiant {organisation_id} n'existe",
        )
        return redirect("switch_main_organisation")

    if organisation.id not in Organisation.objects.filter(
        aidants__pk=aidant.pk
    ).values_list("pk", flat=True):
        django_messages.error(
            request,
            f"Vous ne faites pas partie de l'organisation {organisation.name}",
        )
        return redirect("switch_main_organisation")

    aidant.organisation = organisation
    aidant.save()

    next_url = request.POST.get("next", reverse("espace_aidant_home"))
    next_url = unquote(next_url) if next_url else reverse("espace_aidant_home")

    return HttpResponseRedirect(next_url)
