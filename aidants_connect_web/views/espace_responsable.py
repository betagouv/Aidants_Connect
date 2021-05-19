from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.models import Aidant, CarteTOTP, Organisation
from aidants_connect_web.decorators import (
    user_is_responsable_structure,
    activity_required,
)
from aidants_connect_web.forms import CarteOTPSerialNumberForm, CarteTOTPValidationForm


def check_organisation_and_responsable(responsable: Aidant, organisation: Organisation):
    if responsable not in organisation.responsables.all():
        raise Http404


@login_required
@user_is_responsable_structure
def home(request):
    responsable = request.user
    organisations = (
        Organisation.objects.filter(responsables=responsable)
        .prefetch_related("aidants")
        .order_by("name")
    )

    if organisations.count() == 1:
        organisation = organisations[0]
        return redirect(
            "espace_responsable_organisation", organisation_id=organisation.id
        )

    return render(
        request,
        "aidants_connect_web/espace_responsable/home.html",
        {"responsable": responsable, "organisations": organisations},
    )


@login_required
@user_is_responsable_structure
@activity_required
def organisation(request, organisation_id):
    responsable: Aidant = request.user
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    check_organisation_and_responsable(responsable, organisation)

    aidants = organisation.aidants.order_by("-is_active", "last_name").prefetch_related(
        "carte_totp"
    )
    totp_devices_users = {
        device.user.id: device.confirmed
        for device in TOTPDevice.objects.filter(user__in=aidants)
    }

    return render(
        request,
        "aidants_connect_web/espace_responsable/organisation.html",
        {
            "responsable": responsable,
            "organisation": organisation,
            "aidants": aidants,
            "totp_devices_users": totp_devices_users,
        },
    )


@login_required
@user_is_responsable_structure
@activity_required
def aidant(request, organisation_id, aidant_id):
    responsable: Aidant = request.user
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    check_organisation_and_responsable(responsable, organisation)

    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if aidant.organisation.id != organisation_id:
        raise Http404

    return render(
        request,
        "aidants_connect_web/espace_responsable/aidant.html",
        {"aidant": aidant, "organisation": organisation},
    )


@login_required
@user_is_responsable_structure
@activity_required
def associate_aidant_carte_totp(request, organisation_id, aidant_id):
    responsable: Aidant = request.user
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    check_organisation_and_responsable(responsable, organisation)

    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if aidant.organisation.id != organisation_id:
        raise Http404

    if hasattr(aidant, "carte_totp"):
        django_messages.error(
            request,
            (
                f"Le compte de {aidant.get_full_name()} est déjà associé à une carte "
                "TOTP. Vous devez d’abord retirer la carte de son compte avant de "
                "pouvoir en associer une nouvelle."
            ),
        )
        return redirect(
            "espace_responsable_aidant",
            organisation_id=organisation.id,
            aidant_id=aidant.id,
        )

    if request.method == "GET":
        form = CarteOTPSerialNumberForm()

    if request.method == "POST":
        form = CarteOTPSerialNumberForm(request.POST)
        if form.is_valid():
            serial_number = form.cleaned_data["serial_number"]
            try:
                carte_totp = CarteTOTP.objects.get(serial_number=serial_number)

                with transaction.atomic():
                    carte_totp.aidant = aidant
                    carte_totp.save()
                    totp_device = TOTPDevice(
                        key=carte_totp.seed,
                        user=aidant,
                        step=60,  # todo: some devices may have a different step!
                        confirmed=False,
                        tolerance=30,
                        name=f"Carte n° {serial_number}",
                    )
                    totp_device.save()

                return redirect(
                    "espace_responsable_validate_totp",
                    organisation_id=organisation.id,
                    aidant_id=aidant.id,
                )
            except Exception:
                django_messages.error(
                    request,
                    "Une erreur s’est produite lors de la sauvegarde de la carte.",
                )
                # todo send exception to Sentry

    return render(
        request,
        "aidants_connect_web/espace_responsable/write-carte-totp-sn.html",
        {
            "aidant": aidant,
            "organisation": organisation,
            "responsable": responsable,
            "form": form,
        },
    )


@login_required
@user_is_responsable_structure
@activity_required
def validate_aidant_carte_totp(request, organisation_id, aidant_id):
    responsable: Aidant = request.user
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    check_organisation_and_responsable(responsable, organisation)

    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if aidant.organisation.id != organisation_id:
        raise Http404

    if not hasattr(aidant, "carte_totp"):
        django_messages.error(
            request,
            (
                "Impossible de trouver une carte TOTP associée au compte de "
                f"{aidant.get_full_name()}."
                "Vous devez d’abord associer une carte à son compte."
            ),
        )
        return redirect(
            "espace_responsable_organisation",
            organisation_id=organisation.id,
        )

    if request.method == "POST":
        form = CarteTOTPValidationForm(request.POST)
    else:
        form = CarteTOTPValidationForm()

    if form.is_valid():
        token = form.cleaned_data["otp_token"]
        totp_device = TOTPDevice.objects.get(
            key=aidant.carte_totp.seed, user_id=aidant.id
        )
        valid = totp_device.verify_token(token)
        if valid:
            totp_device.tolerance = 1
            totp_device.confirmed = True
            totp_device.save()
            django_messages.success(
                request,
                (
                    "Tout s’est bien passé, le compte de "
                    f"{aidant.get_full_name()} est prêt !"
                ),
            )
            return redirect(
                "espace_responsable_organisation",
                organisation_id=organisation.id,
            )
        else:
            django_messages.error(request, "Ce code n’est pas valide.")

    return render(
        request,
        "aidants_connect_web/espace_responsable/validate-carte-totp.html",
        {"aidant": aidant, "organisation": organisation, "form": form},
    )
