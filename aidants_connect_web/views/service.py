import logging
from datetime import timedelta
from operator import itemgetter

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from aidants_connect_pico_cms.models import Testimony
from aidants_connect_web.forms import OTPForm
from aidants_connect_web.models import Aidant, Journal, Mandat, Organisation, Usager

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def humanize_demarche_names(name: str) -> str:
    """
    >>> humanize_demarche_names('argent')
    "ARGENT: Crédit immobilier, Impôts, Consommation, Livret A, Assurance, "
            "Surendettement…"
    :param name: Demarche to describe
    :return: Human names and description for demarche
    """
    demarches = settings.DEMARCHES
    return f"{demarches[name]['titre'].upper()}: {demarches[name]['description']}"


def home_page(request):
    if request.GET.get("infolettre", ""):
        django_messages.success(
            request, "Votre inscription à l'infolettre a bien été prise en compte."
        )

    testimonies_qs = Testimony.objects.for_display()
    return render(
        request,
        "public_website/home_page.html",
        context={
            "testimonies": testimonies_qs[:3],
            "has_more_testimonies": testimonies_qs.count() > 3,
        },
    )


@login_required
def logout_page(request):
    logout(request)
    django_messages.success(request, "Vous êtes maintenant déconnecté·e.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


def guide_utilisation(request):
    return render(request, "public_website/guide_utilisation.html")


def habilitation(request):
    return render(request, "public_website/habilitation.html")


def statistiques(request):
    last_30_days = timezone.now() - timedelta(days=30)
    stafforg = settings.STAFF_ORGANISATION_NAME

    def get_usager_ids(query_set) -> list:
        return [query_set_item.usager_id for query_set_item in query_set]

    organisations_accredited_count = (
        Organisation.objects.accredited().exclude(name=stafforg).count()
    )
    organisations_not_accredited_count = (
        Organisation.objects.not_yet_accredited().exclude(name=stafforg).count()
    )

    aidants_count = (
        Aidant.objects.exclude(organisation__name=stafforg)
        .filter(carte_totp__isnull=False)
        .filter(is_active=True)
        .filter(can_create_mandats=True)
        .count()
    )
    aidants_not_accredited_count = (
        Aidant.objects.exclude(organisation__name=stafforg)
        .filter(carte_totp__isnull=True)
        .filter(is_active=True)
        .filter(can_create_mandats=True)
        .count()
    )

    # mandats
    # # mandats prep
    mandats = Mandat.objects.exclude(organisation__name=stafforg)
    active_mandats = mandats.active()

    # # mandat results
    mandat_count = mandats.count()
    active_mandat_count = active_mandats.count()

    # Usagers
    usagers_with_mandat_count = Usager.objects.filter(
        pk__in=get_usager_ids(mandats)
    ).count()
    usagers_with_active_mandat_count = Usager.objects.filter(
        pk__in=get_usager_ids(active_mandats)
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
    demarches_count = [
        {
            "title": settings.DEMARCHES[demarche]["titre_court"],
            "icon": settings.DEMARCHES[demarche]["icon"],
            "value": autorisation_use.filter(demarche=demarche).count(),
        }
        for demarche in settings.DEMARCHES.keys()
    ]

    demarches_count.sort(key=itemgetter("value"), reverse=True)

    chart_labels = [demarche["title"] for demarche in demarches_count]
    chart_values = [demarche["value"] for demarche in demarches_count]
    chart_icons = [demarche["icon"] for demarche in demarches_count]

    chart_data = {"labels": chart_labels, "data": chart_values, "icons": chart_icons}

    return render(
        request,
        "public_website/statistiques.html",
        {
            "data": chart_data,
            "organisations_accredited_count": organisations_accredited_count,
            "organisations_not_accredited_count": organisations_not_accredited_count,
            "aidants_count": aidants_count,
            "aidants_accrediting_count": aidants_not_accredited_count,
            "mandats_count": mandat_count,
            "active_mandats_count": active_mandat_count,
            "usagers_with_mandat_count": usagers_with_mandat_count,
            "usagers_with_active_mandat_count": usagers_with_active_mandat_count,
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


def accessibilite(request):
    return render(request, "public_website/accessibilite.html")


def ressources(request):
    return render(request, "public_website/ressource_page.html")


def faq_generale(request):
    return render(request, "public_website/faq/generale.html")


def faq_mandat(request):
    return render(request, "public_website/faq/mandat.html")


def faq_donnees_personnelles(request):
    return render(request, "public_website/faq/donnees_personnelles.html")


def faq_habilitation(request):
    return render(request, "public_website/faq/habilitation.html")
