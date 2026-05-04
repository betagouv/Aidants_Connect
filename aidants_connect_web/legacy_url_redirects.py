"""
Explicit permanent redirects for historical URL paths.

Each legacy pattern is listed below so changes to espace-aidant / espace-referent
routes can be reviewed against this file. Query strings are preserved.
"""

from django.http import HttpResponsePermanentRedirect
from django.urls import re_path
from django.views import View


def _append_query_string(request, path: str) -> str:
    qs = request.META.get("QUERY_STRING", "")
    return f"{path}?{qs}" if qs else path


class LegacyRootAidantRedirectView(View):
    """Redirect /{segment}/... → /espace-aidant/{segment}/..."""

    segment: str = ""

    def get(self, request, remainder=None):
        rest = remainder or "/"
        if not rest.startswith("/"):
            rest = f"/{rest}"
        new_path = f"/espace-aidant/{self.segment}{rest}"
        return HttpResponsePermanentRedirect(_append_query_string(request, new_path))

    post = get


class LegacyReferentPrefixRedirectView(View):
    """Redirect /espace-responsable/... using an explicit path template."""

    path_template: str = ""

    def get(self, request, **kwargs):
        new_path = self.path_template.format(**kwargs)
        return HttpResponsePermanentRedirect(_append_query_string(request, new_path))

    post = get


# --- Root-level aidant URLs (before /espace-aidant/ prefix) -----------------
# One explicit route per first path segment; remainder is appended unchanged.

LEGACY_ROOT_AIDANT_URLPATTERNS = [
    re_path(
        r"^usagers(?P<remainder>/.*)?$",
        LegacyRootAidantRedirectView.as_view(segment="usagers"),
    ),
    re_path(
        r"^mandats(?P<remainder>/.*)?$",
        LegacyRootAidantRedirectView.as_view(segment="mandats"),
    ),
    re_path(
        r"^renew_mandat(?P<remainder>/.*)?$",
        LegacyRootAidantRedirectView.as_view(segment="renew_mandat"),
    ),
    re_path(
        r"^creation_mandat(?P<remainder>/.*)?$",
        LegacyRootAidantRedirectView.as_view(segment="creation_mandat"),
    ),
    re_path(
        r"^notifications(?P<remainder>/.*)?$",
        LegacyRootAidantRedirectView.as_view(segment="notifications"),
    ),
    re_path(
        r"^logout-callback(?P<remainder>/.*)?$",
        LegacyRootAidantRedirectView.as_view(segment="logout-callback"),
    ),
]

# --- /espace-responsable/ → /espace-referent/ (mirror urls_espace_referent) --
# Order matters: more specific paths before aidant/<id>/.

LEGACY_ESPACE_RESPONSABLE_URLPATTERNS = [
    re_path(
        r"^espace-responsable/?$",
        LegacyReferentPrefixRedirectView.as_view(path_template="/espace-referent/"),
    ),
    re_path(
        r"^espace-responsable/organisation/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/organisation/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidants/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidants/"
        ),
    ),
    re_path(
        r"^espace-responsable/referents/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/referents/"
        ),
    ),
    re_path(
        r"^espace-responsable/organisation/(?P<organisation_id>\d+)/responsables/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/organisation/{organisation_id}/responsables/"  # noqa: E501
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/ajouter/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/ajouter/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/supprimer-carte/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/supprimer-carte/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/ajouter-otp-app/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/ajouter-otp-app/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/supprimer-otp-app/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/supprimer-otp-app/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/changer-organisations/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/changer-organisations/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/supprimer-organisation/"
        r"(?P<organisation_id>\d+)/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/"
            "supprimer-organisation/{organisation_id}/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/reactivate-aidant/"
        r"(?P<organisation_id>\d+)/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/"
            "reactivate-aidant/{organisation_id}/"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/type-carte/?$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/type-carte"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/lier-carte/?$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/lier-carte"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/valider-carte/?$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/valider-carte"
        ),
    ),
    re_path(
        r"^espace-responsable/aidant-a-former/(?P<request_id>\d+)/annuler-demande/?$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant-a-former/{request_id}/annuler-demande"  # noqa: E501
        ),
    ),
    re_path(
        r"^espace-responsable/aidant-a-former/(?P<request_id>\d+)/inscription-formation/$",  # noqa: E501
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant-a-former/{request_id}/inscription-formation/"  # noqa: E501
        ),
    ),
    re_path(
        r"^espace-responsable/aidant/(?P<aidant_id>\d+)/$",
        LegacyReferentPrefixRedirectView.as_view(
            path_template="/espace-referent/aidant/{aidant_id}/"
        ),
    ),
]
