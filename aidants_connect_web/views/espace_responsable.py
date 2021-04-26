from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from aidants_connect_web.models import Organisation
from aidants_connect_web.decorators import (
    user_is_responsable_structure,
    activity_required,
)


def check_organisation_and_responsable(responsable, organisation_id):
    try:
        organisation = Organisation.objects.get(id=organisation_id)
    except Organisation.DoesNotExist:
        raise Http404
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

    return render(
        request,
        "aidants_connect_web/espace_responsable/home.html",
        {"responsable": responsable, "organisations": organisations},
    )


@login_required
@user_is_responsable_structure
@activity_required
def organisation(request, organisation_id):
    responsable = request.user
    check_organisation_and_responsable(responsable, organisation_id)

    organisation = Organisation.objects.get(id=organisation_id)
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
