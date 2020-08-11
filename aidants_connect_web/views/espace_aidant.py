from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def home(request):
    aidant = request.user

    return render(
        request, "aidants_connect_web/espace_aidant/home.html", {"aidant": aidant},
    )


@login_required
def organisation(request):
    aidant = request.user

    organisation = aidant.organisation
    if not organisation:
        django_messages.error(request, "Vous n'êtes pas rattaché à une organisation.")
        return redirect("espace_aidant_home")

    organisation_aidants_active = organisation.aidants.active()

    return render(
        request,
        "aidants_connect_web/espace_aidant/organisation.html",
        {
            "aidant": aidant,
            "organisation": organisation,
            "organisation_aidants_active": organisation_aidants_active,
        },
    )
