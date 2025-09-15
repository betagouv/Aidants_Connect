import logging
from typing import Tuple

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from aidants_connect_pico_cms.models import Testimony
from aidants_connect_web.forms import OTPForm
from aidants_connect_web.models import Aidant, Journal, Mandat, Organisation

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
        context={"testimonies": testimonies_qs[:3]},
    )


@login_required
def logout_page(request):
    logout(request)
    django_messages.success(request, "Vous êtes maintenant déconnecté·e.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


def guide_utilisation(request):
    return render(request, "public_website/guide_utilisation.html")


def formation(request):
    return render(request, "public_website/formation.html")


def habilitation(request):
    return render(request, "public_website/habilitation.html")


class StatistiquesView(TemplateView):
    template_name = "public_website/statistiques.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.autorisation_use_qs = Journal.objects.excluding_staff().filter(
            action="use_autorisation"
        )

        self.active_aidants_qs = (
            Aidant.objects.exclude(organisation__name=settings.STAFF_ORGANISATION_NAME)
            .filter(is_active=True)
            .filter(can_create_mandats=True)
        )

    def get_demarches_stats(self) -> Tuple[dict[str, list], int]:
        data = {"icons": [], "titles": [], "values": []}

        qs = (
            self.autorisation_use_qs.values("demarche")
            .annotate(total=Count("demarche"))
            .order_by("total")
            .all()
        )

        data_total = 0
        demarches_met = []
        for entry in qs.all():
            demarche = settings.DEMARCHES[entry["demarche"]]
            count = entry["total"]
            demarches_met.append(entry["demarche"])
            data["icons"].append(demarche["icon"])
            data["titles"].append(demarche["titre_court"])
            data["values"].append(count)
            data_total += count

        # Fill rest of data with demarches not met
        for k, v in settings.DEMARCHES.items():
            if k in demarches_met:
                continue
            data["icons"].append(v["icon"])
            data["titles"].append(v["titre_court"])
            data["values"].append(0)

        return data, data_total

    def get_context_data(self, **kwargs):
        usagers_helped_count = (
            self.autorisation_use_qs.values("usager").distinct().count()
        )

        mandat_count = Mandat.objects.exclude(
            organisation__name=settings.STAFF_ORGANISATION_NAME
        ).count()

        organisations_accredited_count = (
            Organisation.objects.accredited()
            .exclude(name=settings.STAFF_ORGANISATION_NAME)
            .count()
        )
        organisations_not_accredited_count = (
            Organisation.objects.not_yet_accredited()
            .exclude(name=settings.STAFF_ORGANISATION_NAME)
            .count()
        )

        aidants_count = self.active_aidants_qs.filter(carte_totp__isnull=False).count()
        aidants_not_accredited_count = self.active_aidants_qs.filter(
            carte_totp__isnull=True
        ).count()

        data, data_total = self.get_demarches_stats()

        return super().get_context_data(
            **kwargs,
            usage_section={
                "Démarches administratives réalisées": data_total,
                "Personnes accompagnées": usagers_helped_count,
                "Mandats créés": mandat_count,
            },
            data=data,
            deployment_section=(
                {
                    "Aidants habilités": aidants_count,
                    "Aidants en cours d’habilitation": aidants_not_accredited_count,
                },
                {
                    "Structures habilitées": organisations_accredited_count,
                    "Structures en cours d’habilitation": (
                        organisations_not_accredited_count
                    ),
                },
            ),
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


def politique_confidentialite(request):
    return render(request, "public_website/politique_confidentialite.html")


def mentions_legales(request):
    return render(request, "public_website/mentions_legales.html")


def budget(request):
    return render(request, "public_website/budget.html")


class SitemapView(TemplateView):
    template_name = "public_website/plan_site.html"


class AccessibiliteView(TemplateView):
    template_name = "public_website/accessibilite.html"


def ressources(request):
    return render(
        request,
        "public_website/ressource_page.html",
        {"should_render_testimonies": Testimony.objects.for_display().count() > 0},
    )
