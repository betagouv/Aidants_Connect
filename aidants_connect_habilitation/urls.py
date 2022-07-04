from django.urls import path

from aidants_connect_habilitation.views import (
    AddAidantsRequestView,
    IssuerEmailConfirmationView,
    IssuerEmailConfirmationWaitingView,
    IssuerPageView,
    ModifyIssuerFormView,
    ModifyOrganisationRequestFormView,
    NewHabilitationView,
    NewIssuerFormView,
    NewOrganisationRequestFormView,
    PersonnelRequestFormView,
    ReadonlyRequestView,
    ValidationRequestFormView,
)

urlpatterns = [
    path("nouvelle/", NewHabilitationView.as_view(), name="habilitation_new"),
    path("demandeur/", NewIssuerFormView.as_view(), name="habilitation_new_issuer"),
    path(
        "demandeur/<str:issuer_id>/confirmation-email/confirmer/<str:key>/",
        IssuerEmailConfirmationView.as_view(),
        name="habilitation_issuer_email_confirmation_confirm",
    ),
    path(
        "demandeur/<str:issuer_id>/confirmation-email/en-attente/",
        IssuerEmailConfirmationWaitingView.as_view(),
        name="habilitation_issuer_email_confirmation_waiting",
    ),
    path(
        "demandeur/<str:issuer_id>/",
        IssuerPageView.as_view(),
        name="habilitation_issuer_page",
    ),
    path(
        "demandeur/<str:issuer_id>/modifier/",
        ModifyIssuerFormView.as_view(),
        name="habilitation_modify_issuer",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/nouvelle/",
        NewOrganisationRequestFormView.as_view(),
        name="habilitation_new_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/infos-generales/",
        ModifyOrganisationRequestFormView.as_view(),
        name="habilitation_modify_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidants/",
        PersonnelRequestFormView.as_view(),
        name="habilitation_new_aidants",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/validation/",
        ValidationRequestFormView.as_view(),
        name="habilitation_validation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/voir/",
        ReadonlyRequestView.as_view(),
        name="habilitation_organisation_view",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/ajouter-aidants/",
        AddAidantsRequestView.as_view(),
        name="habilitation_organisation_add_aidants",
    ),
]
