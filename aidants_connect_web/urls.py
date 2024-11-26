from django.urls import include, path, re_path

from magicauth import settings as magicauth_settings
from magicauth.urls import urlpatterns as magicauth_urls

from aidants_connect_web.api.urls import router as api_router
from aidants_connect_web.views import (
    FC_as_FS,
    datapass,
    espace_aidant,
    espace_responsable,
    id_provider,
    login,
    mandat,
    notifications,
    renew_mandat,
    sandbox,
    service,
    sms,
    usagers,
)

urlpatterns = [
    # service
    path("accounts/login/", login.LoginView.as_view(), name="login"),
    path(magicauth_settings.LOGIN_URL, login.LoginRedirect.as_view()),
    path("logout-session/", service.logout_page, name="logout"),
    path("activity_check/", service.activity_check, name="activity_check"),
    # espace aidant : home, organisation
    path("espace-aidant/", espace_aidant.Home.as_view(), name="espace_aidant_home"),
    path(
        "espace-aidant/valider-cgu",
        espace_aidant.ValidateCGU.as_view(),
        name="espace_aidant_cgu",
    ),
    path(
        "espace-aidant/organisations/switch_main",
        espace_aidant.SwitchMainOrganisation.as_view(),
        name="espace_aidant_switch_main_organisation",
    ),
    # usagers
    path("usagers/", usagers.usagers_index, name="usagers"),
    path(
        "usagers/<int:usager_id>/", usagers.UsagerView.as_view(), name="usager_details"
    ),
    path(
        "usagers/<int:usager_id>/autorisations/<int:autorisation_id>/cancel_confirm",
        usagers.confirm_autorisation_cancelation,
        name="confirm_autorisation_cancelation",
    ),
    path(
        "usagers/<int:usager_id>/autorisations/<int:autorisation_id>/cancel_success",
        usagers.autorisation_cancelation_success,
        name="autorisation_cancelation_success",
    ),
    path(
        "usagers/<int:usager_id>/autorisations/<int:autorisation_id>/cancel_attestation",  # noqa: E501
        usagers.autorisation_cancelation_attestation,
        name="autorisation_cancelation_attestation",
    ),
    path(
        "mandats/<int:mandat_id>/cancel_confirm",
        usagers.confirm_mandat_cancelation,
        name="confirm_mandat_cancelation",
    ),
    path(
        "mandats/<int:mandat_id>/cancel_success",
        usagers.mandat_cancelation_success,
        name="mandat_cancelation_success",
    ),
    path(
        "mandats/<int:mandat_id>/attestation_de_revocation",
        usagers.mandat_cancellation_attestation,
        name="mandat_cancellation_attestation",
    ),
    path(
        "mandats/<int:mandat_id>/visualisation",
        mandat.Attestation.as_view(),
        name="mandat_visualisation",
    ),
    # renew mandat
    path(
        "renew_mandat/<int:usager_id>",
        renew_mandat.RenewMandat.as_view(),
        name="renew_mandat",
    ),
    path(
        "renew_mandat/a_distance/demande_consentement/",
        renew_mandat.RemoteConsentSecondStepView.as_view(),
        name="renew_remote_second_step",
    ),
    path(
        "renew_mandat/attente_consentement/",
        renew_mandat.WaitingRoom.as_view(),
        name="renew_mandat_waiting_room",
    ),
    path(
        "renew_mandat/attente_consentement.json/",
        mandat.WaitingRoomJson.as_view(),
        name="renew_mandat_waiting_room_json",
    ),
    # new mandat
    path("creation_mandat/", mandat.NewMandat.as_view(), name="new_mandat"),
    path(
        "creation_mandat/recapitulatif/",
        mandat.NewMandatRecap.as_view(),
        name="new_mandat_recap",
    ),
    path(
        "creation_mandat/a_distance/demande_consentement/",
        mandat.RemoteConsentSecondStepView.as_view(),
        name="new_mandat_remote_second_step",
    ),
    path(
        "creation_mandat/a_distance/attente_consentement/",
        mandat.WaitingRoom.as_view(),
        name="new_mandat_waiting_room",
    ),
    path(
        "creation_mandat/a_distance/attente_consentement.json/",
        mandat.WaitingRoomJson.as_view(),
        name="new_mandat_waiting_room_json",
    ),
    path("logout-callback/", mandat.NewMandatRecap.as_view(), name="logout_callback"),
    path(
        "creation_mandat/visualisation/projet/",
        mandat.AttestationProject.as_view(),
        name="new_attestation_projet",
    ),
    path(
        "creation_mandat/visualisation/final/<int:mandat_id>",
        mandat.Attestation.as_view(),
        name="new_attestation_final",
    ),
    re_path(
        "creation_mandat/qrcode/(?P<mandat_id>[0-9]+)?/?",
        mandat.AttestationQRCode.as_view(),
        name="new_attestation_qrcode",
    ),
    path(
        "creation_mandat/traduction/",
        mandat.Translation.as_view(),
        name="mandate_translation",
    ),
    # id_provider
    path("authorize/", id_provider.Authorize.as_view(), name="authorize"),
    path("token/", id_provider.Token.as_view(), name="token"),
    path("userinfo/", id_provider.user_info, name="user_info"),
    path(
        "select_demarche/",
        id_provider.FISelectDemarche.as_view(),
        name="fi_select_demarche",
    ),
    path(
        "logout/",
        id_provider.end_session_endpoint,
        name="end_session_endpoint",
    ),
    # Espace référent structure
    path(
        "espace-responsable/organisation/",
        espace_responsable.OrganisationView.as_view(),
        name="espace_responsable_organisation",
    ),
    path(
        "espace-responsable/aidants/",
        espace_responsable.AidantsView.as_view(),
        name="espace_responsable_aidants",
    ),
    path(
        "espace-responsable/referents/",
        espace_responsable.ReferentsView.as_view(),
        name="espace_responsable_referents",
    ),
    path(
        "espace-responsable/demandes/",
        espace_responsable.DemandesView.as_view(),
        name="espace_responsable_demandes",
    ),
    path(
        "espace-responsable/organisation/<int:organisation_id>/responsables/",
        espace_responsable.OrganisationResponsables.as_view(),
        name="espace_responsable_organisation_responsables",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/",
        espace_responsable.AidantView.as_view(),
        name="espace_responsable_aidant",
    ),
    path(
        "espace-responsable/aidant/ajouter/",
        espace_responsable.NewHabilitationRequest.as_view(),
        name="espace_responsable_aidant_new",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/supprimer-carte/",
        espace_responsable.RemoveCardFromAidant.as_view(),
        name="espace_responsable_aidant_remove_card",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/ajouter-otp-app/",
        espace_responsable.AddAppOTPToAidant.as_view(),
        name="espace_responsable_aidant_add_app_otp",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/supprimer-otp-app/",
        espace_responsable.RemoveAppOTPFromAidant.as_view(),
        name="espace_responsable_aidant_remove_app_otp",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/changer-organisations/",
        espace_responsable.ChangeAidantOrganisations.as_view(),
        name="espace_responsable_aidant_change_organisations",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/supprimer-organisation/<int:organisation_id>/",  # noqa: E501
        espace_responsable.RemoveAidantFromOrganisationView.as_view(),
        name="espace_responsable_remove_aidant_from_organisation",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/type-carte",
        espace_responsable.ChooseTOTPDevice.as_view(),
        name="espace_responsable_choose_totp",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/lier-carte",
        espace_responsable.AssociateAidantCarteTOTP.as_view(),
        name="espace_responsable_associate_totp",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/valider-carte",
        espace_responsable.ValidateAidantCarteTOTP.as_view(),
        name="espace_responsable_validate_totp",
    ),
    path(
        "espace-responsable/aidant-a-former/<int:request_id>/annuler-demande",
        espace_responsable.CancelHabilitationRequestView.as_view(),
        name="espace_responsable_cancel_habilitation",
    ),
    path(
        "espace-responsable/aidant-a-former/<int:request_id>/inscription-formation/",
        espace_responsable.FormationRegistrationView.as_view(),
        name="espace_responsable_register_formation",
    ),
    # FC_as_FS
    path("fc_authorize/", FC_as_FS.FCAuthorize.as_view(), name="fc_authorize"),
    path("callback/", FC_as_FS.fc_callback, name="fc_callback"),
    # public_website
    path("", service.home_page, name="home_page"),
    path("stats/", service.statistiques, name="statistiques"),
    path("cgu/", service.cgu, name="cgu"),
    path(
        "politique_confidentialite/",
        service.politique_confidentialite,
        name="politique_confidentialite",
    ),
    path("mentions-legales/", service.mentions_legales, name="mentions_legales"),
    path("guide_utilisation/", service.guide_utilisation, name="guide_utilisation"),
    path("formation/", service.formation, name="habilitation_faq_formation"),
    path("habilitation/", service.habilitation, name="habilitation_faq_habilitation"),
    path("ressources/", service.ressources, name="ressources"),
    path("accessibilite/", service.AccessibiliteView.as_view(), name="accessibilite"),
    # # Datapass
    path(
        "datapass_receiver/",
        datapass.organisation_receiver,
        name="datapass_organisation",
    ),
    path(
        "datapass_habilitation/",
        datapass.habilitation_receiver,
        name="datapass_habilitation",
    ),
    path(
        "notifications/",
        notifications.Notifications.as_view(),
        name="notification_list",
    ),
    path(
        "notifications/<int:notification_id>/",
        notifications.NotificationDetail.as_view(),
        name="notification_detail",
    ),
    path(
        "notifications/<int:notification_id>/marquer/",
        notifications.MarkNotification.as_view(),
        name="notification_mark",
    ),
    # # SMS
    # SMS provider may misconfigure the trailing slash so we need to respond on both
    re_path(r"sms/callback/?$", sms.Callback.as_view(), name="sms_callback"),
    # # Bac à sable
    path(
        "bac-a-sable/presentation",
        sandbox.Sandbox.as_view(),
        name="sandbox_presentation",
    ),
    path("api/", include(api_router.urls)),
]

urlpatterns.extend(magicauth_urls)
