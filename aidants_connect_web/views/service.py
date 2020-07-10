from datetime import timedelta
import logging

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from aidants_connect_web.forms import OTPForm
from aidants_connect_web.models import Aidant, Journal, Mandat, Organisation, Usager


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
    return render(request, "public_website/home_page.html",)


@login_required
def logout_page(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def dashboard(request):
    aidant = request.user
    messages = django_messages.get_messages(request)
    return render(
        request,
        "aidants_connect_web/dashboard.html",
        {"aidant": aidant, "messages": messages},
    )


def guide_utilisation(request):
    return render(request, "public_website/guide_utilisation.html")


def statistiques(request):
    last_30_days = timezone.now() - timedelta(days=30)
    stafforg = settings.STAFF_ORGANISATION_NAME

    def get_usager_ids(query_set) -> list:
        return [query_set_item.usager_id for query_set_item in query_set]

    organisations_count = Organisation.objects.exclude(name=stafforg).count()
    aidants_count = Aidant.objects.exclude(is_staff=True).count()

    # mandats
    # # mandats prep
    mandats = Mandat.objects.exclude(organisation__name=stafforg)
    mandats_active = mandats.active()

    # # mandat results
    mandat_count = mandats.count()
    mandat_active_count = mandats_active.count()

    # Usagers
    usagers_with_mandat_count = Usager.objects.filter(
        pk__in=get_usager_ids(mandats)
    ).count()
    usagers_with_mandat_active_count = Usager.objects.filter(
        pk__in=get_usager_ids(mandats_active)
    ).count()

    # Autorisations
    # # Autorisation prep
    autorisation_use = Journal.objects.excluding_staff().filter(
        action="use_autorisation"
    )
    autorisation_use_recent = autorisation_use.filter(creation_date__gte=last_30_days)

    # # Autorisation results
    autorisation_use_count = autorisation_use.count()
    autorisation_use_recent_count = autorisation_use_recent.count()

    usagers_helped_count = Usager.objects.filter(
        pk__in=get_usager_ids(autorisation_use)
    ).count()
    usagers_helped_recent_count = Usager.objects.filter(
        pk__in=get_usager_ids(autorisation_use_recent)
    ).count()

    # # Démarches
    demarches_count = []
    for demarche in settings.DEMARCHES.keys():
        demarches_count.append(
            {
                "title": demarche,
                "icon": settings.DEMARCHES[demarche]["icon"],
                "value": autorisation_use.filter(demarche=demarche).count(),
            }
        )

    demarches_count.sort(key=lambda x: x["value"], reverse=True)

    return render(
        request,
        "public_website/statistiques.html",
        {
            "organisations_count": organisations_count,
            "aidants_count": aidants_count,
            "mandats_count": mandat_count,
            "mandats_active_count": mandat_active_count,
            "usagers_with_mandat_count": usagers_with_mandat_count,
            "usagers_with_mandat_active_count": usagers_with_mandat_active_count,
            "autorisation_use_count": autorisation_use_count,
            "autorisation_use_recent_count": autorisation_use_recent_count,
            "usagers_helped_count": usagers_helped_count,
            "usagers_helped_recent_count": usagers_helped_recent_count,
            "demarches_count": demarches_count,
        },
    )


@login_required()
def activity_check(request):
    next_page = request.GET.get("next", settings.LOGIN_REDIRECT_URL)

    if not url_has_allowed_host_and_scheme(
        next_page, allowed_hosts={request.get_host()}, require_https=True
    ):
        log.warning(
            "[Aidants Connect] an unsafe URL was used through the activity check"
        )
        return HttpResponseNotFound()

    aidant = request.user
    if request.method == "POST":
        form = OTPForm(aidant=aidant, data=request.POST)

        if form.is_valid():
            Journal.log_activity_check(aidant)
            return redirect(next_page)
    else:
        form = OTPForm(request.user)

    return render(
        request, "login/activity_check.html", {"form": form, "aidant": aidant}
    )


def cgu(request):
    return render(request, "public_website/cgu.html")


def mentions_legales(request):
    return render(request, "public_website/mentions_legales.html")


def ressources(request):
    return render(request, "public_website/ressource_page.html")


def about(request):
    return render(request, "public_website/about_page.html")


def faq_generale(request):
    return render(request, "public_website/faq/generale.html")


def faq_mandat(request):
    return render(request, "public_website/faq/mandat.html")


def faq_donnees_personnelles(request):
    return render(request, "public_website/faq/donnees_personnelles.html")
