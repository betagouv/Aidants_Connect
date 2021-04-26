from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404

from aidants_connect_web.models import Aidant, Organisation
from aidants_connect_web.decorators import (
    user_is_responsable_structure,
    activity_required,
)


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
