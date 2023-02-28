from django.conf import settings
from django.urls import path, re_path

from magicauth.urls import urlpatterns as magicauth_urls

from aidants_connect_web.views import (
    FC_as_FS,
    datapass,
    espace_aidant,
    espace_responsable,
    id_provider,
    login,
    mandat,
    renew_mandat,
    service,
    sms,
    usagers,
)

urlpatterns = [
    # service
    path("accounts/login/", login.LoginView.as_view(), name="login"),
    path("logout-session/", service.logout_page, name="logout"),
    path("activity_check/", service.activity_check, name="activity_check"),
    # espace aidant : home, organisation
    path("espace-aidant/", espace_aidant.home, name="espace_aidant_home"),
    path(
        "espace-aidant/organisation/",
        espace_aidant.organisation,
        name="espace_aidant_organisation",
    ),
    path(
        "espace-aidant/valider-cgu",
        espace_aidant.validate_cgus,
        name="espace_aidant_cgu",
    ),
    path(
        "espace-aidant/organisations/switch_main",
        espace_aidant.switch_main_organisation,
        name="espace_aidant_switch_main_organisation",
    ),
    # usagers
    path("usagers/", usagers.usagers_index, name="usagers"),
    path("usagers/<int:usager_id>/", usagers.usager_details, name="usager_details"),
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
        "usagers/<int:usager_id>/autorisations/"
        "<int:autorisation_id>/cancel_attestation",
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
        mandat.attestation_visualisation,
        name="mandat_visualisation",
    ),
    # renew mandat
    path(
        "renew_mandat/<int:usager_id>",
        renew_mandat.RenewMandat.as_view(),
        name="renew_mandat",
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
    path(
        "clear_connection/",
        mandat.ClearConnectionView.as_view(),
        name="clear_connection",
    ),
    path("creation_mandat/", mandat.NewMandat.as_view(), name="new_mandat"),
    path(
        "creation_mandat/recapitulatif/",
        mandat.NewMandatRecap.as_view(),
        name="new_mandat_recap",
    ),
    path(
        "creation_mandat/attente_consentement/",
        mandat.WaitingRoom.as_view(),
        name="new_mandat_waiting_room",
    ),
    path(
        "creation_mandat/attente_consentement.json/",
        mandat.WaitingRoomJson.as_view(),
        name="new_mandat_waiting_room_json",
    ),
    path("logout-callback/", mandat.NewMandatRecap.as_view(), name="new_mandat_recap"),
    path(
        "creation_mandat/visualisation/projet/",
        mandat.AttestationProject.as_view(),
        name="new_attestation_projet",
    ),
    path(
        "creation_mandat/succes/",
        mandat.NewMandateSuccess.as_view(),
        name="new_mandat_success",
    ),
    path(
        "creation_mandat/visualisation/final/",
        mandat.attestation_final,
        name="new_attestation_final",
    ),
    path(
        "creation_mandat/qrcode/",
        mandat.attestation_qrcode,
        name="new_attestation_qrcode",
    ),
    # id_provider
    path("authorize/", id_provider.Authorize.as_view(), name="authorize"),
    path("token/", id_provider.token, name="token"),
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
    # Espace responsable structure
    path(
        "espace-responsable/", espace_responsable.home, name="espace_responsable_home"
    ),
    path(
        "espace-responsable/organisation/<int:organisation_id>/",
        espace_responsable.organisation,
        name="espace_responsable_organisation",
    ),
    path(
        "espace-responsable/organisation/<int:organisation_id>/responsables/",
        espace_responsable.organisation_responsables,
        name="espace_responsable_organisation_responsables",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/",
        espace_responsable.aidant,
        name="espace_responsable_aidant",
    ),
    path(
        "espace-responsable/aidant/ajouter/",
        espace_responsable.new_habilitation_request,
        name="espace_responsable_aidant_new",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/supprimer-carte/",
        espace_responsable.remove_card_from_aidant,
        name="espace_responsable_aidant_remove_card",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/changer-organisations/",
        espace_responsable.change_aidant_organisations,
        name="espace_responsable_aidant_change_organisations",
    ),
    path(
        (
            "espace-responsable/aidant/<int:aidant_id>/"
            "supprimer-organisation/<int:organisation_id>/"
        ),
        espace_responsable.remove_aidant_from_organisation,
        name="espace_responsable_remove_aidant_from_organisation",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/lier-carte",
        espace_responsable.associate_aidant_carte_totp,
        name="espace_responsable_associate_totp",
    ),
    path(
        "espace-responsable/aidant/<int:aidant_id>/valider-carte",
        espace_responsable.validate_aidant_carte_totp,
        name="espace_responsable_validate_totp",
    ),
    # FC_as_FS
    path("fc_authorize/", FC_as_FS.fc_authorize, name="fc_authorize"),
    path("callback/", FC_as_FS.fc_callback, name="fc_callback"),
    # public_website
    path("", service.home_page, name="home_page"),
    path("stats/", service.statistiques, name="statistiques"),
    path("cgu/", service.cgu, name="cgu"),
    path("mentions-legales/", service.mentions_legales, name="mentions_legales"),
    path("guide_utilisation/", service.guide_utilisation, name="guide_utilisation"),
    path("habilitation", service.habilitation, name="habilitation"),
    path("ressources/", service.ressources, name="ressources"),
    path("accessibilite/", service.accessibilite, name="accessibilite"),
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
    # # SMS
    # SMS provider may misconfigure the trailing slash so we need to respond on both
    re_path(r"sms/callback/?$", sms.Callback.as_view(), name="sms_callback"),
]

if not settings.FF_USE_PICO_CMS_FOR_FAQ:
    faq_urls = [
        path("faq/mandat/", service.faq_mandat, name="faq_mandat"),
        path(
            "faq/donnees-personnelles/",
            service.faq_donnees_personnelles,
            name="faq_donnees_personnelles",
        ),
        path(
            "faq/habilitation/",
            service.faq_habilitation,
            name="faq_habilitation",
        ),
    ]
    urlpatterns.extend(faq_urls)

urlpatterns.extend(magicauth_urls)
