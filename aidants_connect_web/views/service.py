import logging
from secrets import token_urlsafe

from django.utils import timezone
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
    # Indicateurs de base
    organisation_total = Organisation.objects.count()
    aidant_total = Aidant.objects.count()
    usager_total = Usager.objects.count()
    # Mandats
    mandat_total = Mandat.objects.count()
    mandat_current_total = Mandat.objects.current().count()
    # mandat_used_last_30_days = Mandat.objects.count()
    # Usagers
    usagers_total = Usager.objects.count()
    usager_with_mandat_current = Usager.objects.active().count()

    return render(
        request,
        "aidants_connect_web/statistiques.html",
        {
            "statistiques": [
                {
                    "name": "Indicateurs de base",
                    "values": [
                        {
                            "title": "Organisations",
                            "value": organisation_total
                        },
                        {
                            "title": "Aidants",
                            "value": aidant_total
                        },
                        {
                            "title": "Usagers",
                            "value": usager_total
                        },
                    ],
                },
                {
                    "name": "Mandats",
                    "values": [
                        {
                            "title": "Total",
                            "value": mandat_total
                        },
                        {
                            "title": "Actifs",
                            "value": mandat_current_total
                        },
                        {
                            "title": "Utilisés récemment",
                            "subtitle": "30 derniers jours",
                            "value": '~' # mandat_used_last_30_days
                        },
                    ],
                },
                {
                    "name": "Usagers",
                    "values": [
                        {
                            "title": "Total",
                            "value": usager_total
                        },
                        {
                            "title": "Actifs",
                            "subtitle": "Au moins 1 mandat actif",
                            "value": usager_with_mandat_current
                        }
                    ]
                }   
            ]
        }
    )
