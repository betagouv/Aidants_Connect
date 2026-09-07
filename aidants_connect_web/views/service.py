import json
import logging
import math
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

from aidants_connect_common.constants import AuthorizationDurationChoices
from aidants_connect_pico_cms.models import Testimony
from aidants_connect_web.forms import OTPForm
from aidants_connect_web.models import Aidant, Journal, Mandat, Organisation
from aidants_connect_web.statistics import (
    DEMARCHES_EVOLUTION_MONTHS,
    MANDATS_EVOLUTION_MONTHS,
    OPERATIONAL_AIDANTS_EVOLUTION_MONTHS,
    PERSONNES_ACCOMPAGNEES_EVOLUTION_MONTHS,
    STRUCTURES_HABILITEES_EVOLUTION_MONTHS,
    get_monthly_series,
    get_operational_aidants_monthly_series,
    get_personnes_accompagnees_monthly_series,
    get_structures_habilitees_monthly_series,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def _build_evolution_transcription(series: dict[str, list]) -> list[dict]:
    """Turn an evolution series into accessible transcription rows.

    Each row exposes both the monthly increase and the cumulative total so the
    transcription stays readable even though the chart line is cumulative.
    """
    return [
        {"month": month, "monthly": monthly, "cumulative": cumulative}
        for month, monthly, cumulative in zip(
            series["labels"], series["monthly"], series["cumulative"]
        )
    ]


def _dsfr_bar_chart_props(
    titles: list,
    values: list,
    name: str,
    *,
    horizontal: bool = False,
    aspect_ratio: str = "2",
) -> dict[str, str]:
    props = {
        "x": json.dumps([titles], ensure_ascii=False),
        "y": json.dumps([values], ensure_ascii=False),
        "name": json.dumps([name], ensure_ascii=False),
        "aspect_ratio": aspect_ratio,
    }
    if horizontal:
        props["horizontal"] = "true"
    return props


def _dsfr_bar_line_chart_props(
    series: dict[str, list],
    *,
    name_line: str,
    aspect_ratio: str = "2.5",
) -> dict[str, str]:
    return {
        "x": json.dumps(series["labels"], ensure_ascii=False),
        "y_bar": json.dumps(series["monthly"], ensure_ascii=False),
        "y_line": json.dumps(series["cumulative"], ensure_ascii=False),
        "name_line": f"{name_line} (total cumulé)",
        "aspect_ratio": aspect_ratio,
    }


def humanize_demarche_names(name: str) -> str:
    """
    >>> humanize_demarche_names('argent')
    "ARGENT: Crédit immobilier, Impôts, Consommation, Livret A, Assurance, "
            "Surendettement…"
    :param name: Demarche to describe
    :return: Human names and description for demarche
    """
    demarches = settings.DEMARCHES
    return f"{demarches[name]['titre'].upper()} : {demarches[name]['description']}"


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
    django_messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


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
        data = {"titles": [], "values": []}

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
            data["titles"].append(demarche["titre_court"])
            data["values"].append(count)
            data_total += count

        # Fill rest of data with demarches not met
        for k, v in settings.DEMARCHES.items():
            if k in demarches_met:
                continue
            data["titles"].append(v["titre_court"])
            data["values"].append(0)

        return data, data_total

    def get_mandat_durees_stats(self) -> dict[str, list]:
        counts_by_duree = {
            entry["duree_keyword"]: entry["total"]
            for entry in Mandat.objects.exclude(
                organisation__name=settings.STAFF_ORGANISATION_NAME
            )
            .values("duree_keyword")
            .annotate(total=Count("duree_keyword"))
        }

        short_labels = {
            AuthorizationDurationChoices.SHORT: "1 jour",
            AuthorizationDurationChoices.MONTH: "1 mois",
            AuthorizationDurationChoices.SEMESTER: "6 mois",
            AuthorizationDurationChoices.LONG: "1 an",
        }
        # CSS class keys (colors live in statistics.css; widths use a nonce'd <style>)
        segment_meta = {
            "1 jour": {"key": "short", "color": "#008C7A", "label_on_dark": True},
            "1 mois": {"key": "month", "color": "#000091", "label_on_dark": True},
            "1 an": {"key": "long", "color": "#7BA8F5", "label_on_dark": False},
            "6 mois": {"key": "semester", "color": "#FF9B73", "label_on_dark": False},
            "Autre durée": {"key": "other", "color": "#FFE0C4", "label_on_dark": False},
        }

        counts_by_label: dict[str, int] = {
            label: counts_by_duree.get(keyword, 0)
            for keyword, label in short_labels.items()
        }
        other_count = counts_by_duree.get(
            AuthorizationDurationChoices.EUS_03_20, 0
        ) + counts_by_duree.get(None, 0)
        if other_count:
            counts_by_label["Autre durée"] = other_count

        entries = sorted(
            counts_by_label.items(), key=lambda item: item[1], reverse=True
        )
        values = [value for _, value in entries]
        total = sum(values)
        percentages = self._distribute_percentages(values)

        segments = []
        for (label, value), percent in zip(entries, percentages):
            meta = segment_meta[label]
            segments.append(
                {
                    "key": meta["key"],
                    "label": label,
                    "value": value,
                    "percent": percent,
                    "color": meta["color"],
                    "show_label": _mandat_duree_label_fits(label, percent),
                    "label_on_dark": meta["label_on_dark"],
                }
            )

        return {
            "titles": [label for label, _ in entries],
            "values": values,
            "total": total,
            "segments": segments,
            "has_legend": any(
                not segment["show_label"] and segment["value"] > 0
                for segment in segments
            ),
        }

    @staticmethod
    def _distribute_percentages(values: list[int]) -> list[int]:
        """Round percentages to integers that still sum to 100."""
        total = sum(values)
        if total == 0:
            return [0 for _ in values]

        raw = [value * 100 / total for value in values]
        floors = [int(percent) for percent in raw]
        remainder = 100 - sum(floors)
        by_fraction = sorted(
            enumerate(raw),
            key=lambda item: item[1] - floors[item[0]],
            reverse=True,
        )
        for index, _ in by_fraction[:remainder]:
            floors[index] += 1
        return floors

    def get_context_data(self, **kwargs):
        usagers_helped_count = (
            self.autorisation_use_qs.values("usager").distinct().count()
        )

        mandat_count = Mandat.objects.exclude(
            organisation__name=settings.STAFF_ORGANISATION_NAME
        ).count()
        # active_mandat_count = (
        #     Mandat.objects.exclude(organisation__name=settings.STAFF_ORGANISATION_NAME)
        #     .active()
        #     .count()
        # )

        organisations_accredited_count = (
            Organisation.objects.accredited()
            .exclude(name=settings.STAFF_ORGANISATION_NAME)
            .count()
        )

        aidants_count = self.active_aidants_qs.count()

        data, data_total = self.get_demarches_stats()
        demarches_transcription = [
            {"title": title, "value": value}
            for title, value in zip(data["titles"], data["values"])
        ]
        mandat_durees_data = self.get_mandat_durees_stats()
        mandats_qs = Mandat.objects.exclude(
            organisation__name=settings.STAFF_ORGANISATION_NAME
        )
        mandats_evolution_data = get_monthly_series(
            mandats_qs, "creation_date", months=MANDATS_EVOLUTION_MONTHS
        )
        mandats_evolution_transcription = _build_evolution_transcription(
            mandats_evolution_data
        )
        demarches_evolution_data = get_monthly_series(
            self.autorisation_use_qs, "creation_date", months=DEMARCHES_EVOLUTION_MONTHS
        )
        demarches_evolution_transcription = _build_evolution_transcription(
            demarches_evolution_data
        )
        personnes_accompagnees_evolution_data = (
            get_personnes_accompagnees_monthly_series(
                self.autorisation_use_qs,
                months=PERSONNES_ACCOMPAGNEES_EVOLUTION_MONTHS,
            )
        )
        personnes_accompagnees_evolution_transcription = _build_evolution_transcription(
            personnes_accompagnees_evolution_data
        )
        operational_aidants_evolution_data = get_operational_aidants_monthly_series(
            months=OPERATIONAL_AIDANTS_EVOLUTION_MONTHS
        )
        operational_aidants_evolution_transcription = _build_evolution_transcription(
            operational_aidants_evolution_data
        )
        structures_habilitees_evolution_data = get_structures_habilitees_monthly_series(
            months=STRUCTURES_HABILITEES_EVOLUTION_MONTHS
        )
        structures_habilitees_evolution_transcription = _build_evolution_transcription(
            structures_habilitees_evolution_data
        )
        demarches_realisees_since_date = (
            self.autorisation_use_qs.order_by("creation_date")
            .values_list("creation_date", flat=True)
            .first()
        )

        return super().get_context_data(
            **kwargs,
            usage_section={
                "Démarches réalisées": data_total,
                "Personnes accompagnées": usagers_helped_count,
                "Mandats": mandat_count,
                "Aidants habilités": aidants_count,
                "Structures habilitées": organisations_accredited_count,
            },
            data=data,
            demarches_chart=_dsfr_bar_chart_props(
                data["titles"],
                data["values"],
                "Nombre de démarches",
                aspect_ratio="3",
            ),
            demarches_transcription=demarches_transcription,
            mandat_durees_data=mandat_durees_data,
            mandats_evolution_data=mandats_evolution_data,
            mandats_evolution_chart=_dsfr_bar_line_chart_props(
                mandats_evolution_data,
                name_line="Mandats créés",
            ),
            mandats_evolution_transcription=mandats_evolution_transcription,
            demarches_evolution_data=demarches_evolution_data,
            demarches_evolution_chart=_dsfr_bar_line_chart_props(
                demarches_evolution_data,
                name_line="Démarches réalisées",
            ),
            demarches_evolution_transcription=demarches_evolution_transcription,
            personnes_accompagnees_evolution_data=personnes_accompagnees_evolution_data,
            personnes_accompagnees_evolution_chart=_dsfr_bar_line_chart_props(
                personnes_accompagnees_evolution_data,
                name_line="Personnes accompagnées",
            ),
            personnes_accompagnees_evolution_transcription=(
                personnes_accompagnees_evolution_transcription
            ),
            operational_aidants_evolution_data=operational_aidants_evolution_data,
            operational_aidants_evolution_chart=_dsfr_bar_line_chart_props(
                operational_aidants_evolution_data,
                name_line="Aidants habilités",
            ),
            operational_aidants_evolution_transcription=(
                operational_aidants_evolution_transcription
            ),
            structures_habilitees_evolution_data=structures_habilitees_evolution_data,
            structures_habilitees_evolution_chart=_dsfr_bar_line_chart_props(
                structures_habilitees_evolution_data,
                name_line="Structures habilitées",
            ),
            structures_habilitees_evolution_transcription=(
                structures_habilitees_evolution_transcription
            ),
            demarches_realisees_since_date=demarches_realisees_since_date,
            dsfr_chart_css_url=settings.DSFR_CHART_CSS_URL,
            dsfr_chart_js_url=settings.DSFR_CHART_JS_URL,
        )


def _mandat_duree_label_fits(label: str, percent: int) -> bool:
    """Return True when the segment is wide enough for an in-bar label."""
    label_text = f"{label} · {percent} %"
    # ~0.7 % of bar width per character at typical desktop sizes, plus padding
    min_percent = max(8, math.ceil(len(label_text) * 0.7) + 2)
    return percent >= min_percent


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
        {
            "should_render_testimonies": Testimony.objects.for_display().count() > 0,
            "TUTORIEL_INTERACTIF_URL": settings.EMAIL_WELCOME_AIDANT_TUTORIEL_INTERACTIF,  # noqa: E501
        },
    )
