import logging
from secrets import token_urlsafe

from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.messages import get_messages

from aidants_connect_web.models import (
    Organisation,
    Aidant,
    Usager,
    Mandat
)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def humanize_demarche_names(name: str) -> str:
    """
    >>> humanize_demarche_names('argent')
    "ARGENT: Crédit immobilier, Impôts, Consommation, Livret A, Assurance, "
            "Surendettement…"
    :param machine_names:
    :return: list of human names and description
    """
    demarches = settings.DEMARCHES
    return f"{demarches[name]['titre'].upper()}: {demarches[name]['description']}"


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request,
        "aidants_connect_web/home_page.html",
        {"random_string": random_string, "aidant": request.user},
    )


@login_required
def logout_page(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def dashboard(request):
    aidant = request.user
    messages = get_messages(request)
    return render(
        request,
        "aidants_connect_web/dashboard.html",
        {"aidant": aidant, "messages": messages},
    )


def resources(request):
    return render(request, "aidants_connect_web/resources.html")


def statistiques(request):
    organisation_total = Organisation.objects.count()
    aidant_total = Aidant.objects.count()
    usager_total = Usager.objects.count()
    mandat_total = Mandat.objects.count()

    return render(
        request,
        "aidants_connect_web/statistiques.html",
        {
            "statistiques": {
                "organisation_data": {
                    "name": "Organisations",
                    "total": organisation_total
                },
                "aidant_data": {
                    "name": "Aidants",
                    "total": aidant_total
                },
                "usager_data": {
                    "name": "Usagers",
                    "total": usager_total
                },
                "mandat_data": {
                    "name": "Mandats",
                    "total": mandat_total
                },
            }
        }
    )
