from django.urls import path

from aidants_connect_habilitation.views import (
    AidantFormationRegistrationView,
    HabilitationRequestCancelationView,
    IssuerEmailConfirmationView,
    IssuerEmailConfirmationWaitingView,
    IssuerPageView,
    ManagerFormationRegistrationView,
    ModifyIssuerFormView,
    ModifyOrganisationRequestFormView,
    NewHabilitationView,
    NewIssuerFormView,
    NewOrganisationRequestFormView,
    NewOrganisationSiretVerificationRequestFormView,
    NewOrganisationSiretVerificationTwoRequestFormView,
    PersonnelRequestFormView,
    ReadonlyRequestView,
    ReferentRequestFormView,
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
        "demandeur/<str:issuer_id>/organisation/siret_verification_two/<str:siret>/",
        NewOrganisationSiretVerificationTwoRequestFormView.as_view(),
        name="habilitation_siret_verification_two",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/siret_verification/",
        NewOrganisationSiretVerificationRequestFormView.as_view(),
        name="habilitation_siret_verification",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/nouvelle/<str:siret>/",
        NewOrganisationRequestFormView.as_view(),
        name="habilitation_new_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/infos-generales/",
        ModifyOrganisationRequestFormView.as_view(),
        name="habilitation_modify_organisation",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/referent/",
        ReferentRequestFormView.as_view(),
        name="habilitation_new_referent",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidants/",
        PersonnelRequestFormView.as_view(),
        name="habilitation_new_aidants",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidant/<int:aidant_id>/inscription-formation/",  # noqa E501
        AidantFormationRegistrationView.as_view(),
        name="habilitation_new_aidant_formation_registration",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidant/<int:aidant_id>/annuler-demande/",  # noqa E501
        HabilitationRequestCancelationView.as_view(),
        name="habilitation_new_aidant_cancel_habilitation_request",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/referent/inscription-formation/",  # noqa E501
        ManagerFormationRegistrationView.as_view(),
        name="habilitation_manager_formation_registration",
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
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/modifier-demandeur/",
        ModifyIssuerFormView.as_view(),
        name="habilitation_modify_issuer_on_organisation",
    ),
]
