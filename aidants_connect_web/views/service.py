import logging
from secrets import token_urlsafe

from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.messages import get_messages

from aidants_connect_web.models import Mandat


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def humanize_demarche_names(machine_names: list) -> list:
    """
    >>> humanize_demarche_names(['argent'])
    ["ARGENT: Crédit immobilier, Impôts, Consommation, Livret A, Assurance, "
            "Surendettement…"]
    :param machine_names:
    :return: list of human names and description
    """
    demarches_list = settings.DEMARCHES
    return [
        f"{demarches_list[machine_name]['titre'].upper()}: "
        f"{demarches_list[machine_name]['description']}"
        for machine_name in machine_names
    ]


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request, "aidants_connect_web/home_page.html", {"random_string": random_string}
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


@login_required
def mandats(request):
    messages = get_messages(request)
    aidant = request.user
    mandats = Mandat.objects.all().filter(aidant=aidant).order_by("creation_date")

    for mandat in mandats:
        mandat.perimeter_names = humanize_demarche_names(mandat.perimeter)
    # todo change the "mois" in "jours"
    return render(
        request,
        "aidants_connect_web/mandats.html",
        {"aidant": aidant, "mandats": mandats, "messages": messages},
    )
