from django.urls import path

from aidants_connect_habilitation.views import (
    IssuerFormView,
    NewHabilitationView,
    OrganisationRequestFormView,
    AidantsRequestFormView,
)

urlpatterns = [
    path("nouvelle/", NewHabilitationView.as_view(), name="habilitation_new"),
    path("demandeur/", IssuerFormView.as_view(), name="habilitation_new_issuer"),
    path(
        "demandeur/<str:issuer_id>/",
        IssuerFormView.as_view(),
        name="habilitation_modify_issuer",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/nouvelle/",
        OrganisationRequestFormView.as_view(),
        name="habilitation_new_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:draft_id>/",
        OrganisationRequestFormView.as_view(),
        name="habilitation_modify_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:draft_id>/aidants/",
        AidantsRequestFormView.as_view(),
        name="habilitation_new_aidants",
    ),
]
