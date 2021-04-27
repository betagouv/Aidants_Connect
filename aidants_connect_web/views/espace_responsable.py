from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.models import Aidant, CarteTOTP, Organisation
from aidants_connect_web.decorators import (
    user_is_responsable_structure,
    activity_required,
)
from aidants_connect_web.forms import CarteOTPSerialNumberForm


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

    organisation = Organisation.objects.get(id=organisation_id)
    aidants = organisation.aidants.order_by("-is_active", "last_name").prefetch_related(
        "carte_totp"
    )

    return render(
        request,
        "aidants_connect_web/espace_responsable/organisation.html",
        {
            "responsable": responsable,
            "organisation": organisation,
            "aidants": aidants,
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

    organisation = Organisation.objects.get(id=organisation_id)
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

    # todo check if aidant already has an associated carte TOTP:
    # in that case, we should redirect to "un-associate" first

    if request.method == "GET":
        form = CarteOTPSerialNumberForm()
    else:
        form = CarteOTPSerialNumberForm(request.POST)

    if request.method == "POST" and form.is_valid():
        serial_number = form.cleaned_data["serial_number"]
        try:
            carte_totp = CarteTOTP.objects.get(serial_number=serial_number)

            carte_totp.aidant = aidant
            carte_totp.save()

            totp_device = TOTPDevice(key=carte_totp.seed, user=aidant)
            totp_device.save()

            return redirect(
                "espace_responsable_organisation", organisation_id=organisation.id
            )
        except Exception:
            # Todo display an explanation on what happened exactly
            return render(
                request,
                "aidants_connect_web/espace_responsable/write-carte-totp-sn.html",
                {"aidant": aidant, "organisation": organisation, "form": form},
            )

    return render(
        request,
        "aidants_connect_web/espace_responsable/write-carte-totp-sn.html",
        {"aidant": aidant, "organisation": organisation, "form": form},
    )
