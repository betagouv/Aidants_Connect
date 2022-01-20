from django.urls import path

from aidants_connect_habilitation.views import (
    ModifyIssuerFormView,
    ModifyOrganisationRequestFormView,
    NewIssuerFormView,
    NewHabilitationView,
    NewOrganisationRequestFormView,
    AidantsRequestFormView,
)

urlpatterns = [
    path("nouvelle/", NewHabilitationView.as_view(), name="habilitation_new"),
    path("demandeur/", NewIssuerFormView.as_view(), name="habilitation_new_issuer"),
    path(
        "demandeur/<str:issuer_id>/",
        ModifyIssuerFormView.as_view(),
        name="habilitation_modify_issuer",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/nouvelle/",
        NewOrganisationRequestFormView.as_view(),
        name="habilitation_new_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:draft_id>/",
        ModifyOrganisationRequestFormView.as_view(),
        name="habilitation_modify_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:draft_id>/aidants/",
        AidantsRequestFormView.as_view(),
        name="habilitation_new_aidants",
    ),
]
