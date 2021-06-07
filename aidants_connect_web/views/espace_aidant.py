from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from aidants_connect_web.forms import ValidateCGUForm


@login_required
def home(request):
    aidant = request.user

    return render(
        request,
        "aidants_connect_web/espace_aidant/home.html",
        {"aidant": aidant},
    )


@login_required
def organisation(request):
    aidant = request.user

    organisation = aidant.organisation
    if not organisation:
        django_messages.error(request, "Vous n'êtes pas rattaché à une organisation.")
        return redirect("espace_aidant_home")

    organisation_active_aidants = organisation.aidants.active()

    return render(
        request,
        "aidants_connect_web/espace_aidant/organisation.html",
        {
            "aidant": aidant,
            "organisation": organisation,
            "organisation_active_aidants": organisation_active_aidants,
        },
    )


@login_required
def validate_cgus(request):
    aidant = request.user
    form = ValidateCGUForm()
    if request.method == "POST":
        form = ValidateCGUForm(request.POST)
        if form.is_valid():
            aidant.validated_cgu_version = settings.CGU_CURRENT_VERSION
            aidant.save()
            django_messages.success(
                request, "Merci d’avoir validé les CGU Aidants Connect."
            )
            return redirect("espace_aidant_home")

    return render(
        request,
        "aidants_connect_web/espace_aidant/validate_cgu.html",
        {
            "aidant": aidant,
            "form": form,
        },
    )
