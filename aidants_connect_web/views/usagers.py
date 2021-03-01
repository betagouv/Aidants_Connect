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
        "aidants_connect_web/usagers.html",
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


@login_required
@activity_required
def mandat_cancellation_attestation(request, mandat_id):
    organisation = request.user.organisation
    try:
        mandat = Mandat.objects.get(pk=mandat_id, organisation=organisation)
        if not mandat.autorisations.all().exclude(revocation_date=None):
            return redirect("espace_aidant_home")

    except Mandat.DoesNotExist:
        django_messages.error(request, "Ce mandat est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")
    usager = mandat.usager

    return render(
        request,
        "aidants_connect_web/mandat_cancellation_attestation.html",
        {
            "organisation": organisation,
            "usager_name": usager.get_full_name(),
            "mandat": mandat,
            "creation_date": mandat.creation_date.strftime("%d/%m/%Y à %Hh%M"),
        },
    )
