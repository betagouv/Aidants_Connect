from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from aidants_connect_web.forms import ValidateCGUForm
from aidants_connect_web.models import Aidant, Journal, Organisation
from aidants_connect_web.decorators import activity_required, user_is_aidant


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

    organisation_active_aidants = organisation.current_aidants.active()

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
        new_organisation = Organisation.objects.get(pk=organisation_id)
        if new_organisation not in aidant.organisations.all():
            raise Organisation.DoesNotExist()
    except Organisation.DoesNotExist:
        django_messages.error(
            request,
            "Il est impossible de vous assigner l'organisation numéro "
            f"{organisation_id}",
        )
        return redirect("espace_aidant_switch_main_organisation")

    previous_org = aidant.organisation
    aidant.organisation = new_organisation
    aidant.save()
    Journal.log_switch_organisation(aidant, previous_org)

    default_next = reverse("espace_aidant_home")
    next_url = request.POST.get("next", default_next)
    next_url = unquote(next_url) if next_url else default_next

    return HttpResponseRedirect(next_url)
