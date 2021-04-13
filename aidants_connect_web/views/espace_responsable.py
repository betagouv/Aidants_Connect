from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from aidants_connect_web.models import Organisation
from aidants_connect_web.decorators import (
    user_is_responsable_structure,
    activity_required,
)


@login_required
@user_is_responsable_structure
def home(request):
    responsable = request.user

    return render(
        request,
        "aidants_connect_web/espace_responsable/home.html",
        {"responsable": responsable},
    )


@login_required
@user_is_responsable_structure
@activity_required
def organisation(request, organisation_id):
    responsable = request.user
    organisation = Organisation.objects.get(id=organisation_id)
    if not organisation:
        django_messages.error(request, "Vous n'êtes pas rattaché à une organisation.")
        return redirect("espace_aidant_home")

    organisation_active_aidants = organisation.aidants.active()
    return render(
        request,
        "aidants_connect_web/espace_responsable/organisation.html",
        {
            "responsable": responsable,
            "organisation": organisation,
            "organisation_active_aidants": organisation_active_aidants,
        },
    )
