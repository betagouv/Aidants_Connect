from django.urls import path

from magicauth import views as magicauth_views
from magicauth.urls import urlpatterns as magicauth_urls

from aidants_connect_web.views import (
    FC_as_FS,
    id_provider,
    new_mandat,
    service,
    usagers,
)

urlpatterns = [
    # service
    path("", service.home_page, name="home_page"),
    path("accounts/login/", magicauth_views.LoginView.as_view(), name="login"),
    path("dashboard/", service.dashboard, name="dashboard"),
    # usagers
    path("usagers/", usagers.usagers_index, name="usagers"),
    path("usagers/<int:usager_id>/", usagers.usager_details, name="usager_details"),
    path(
        "usagers/<int:usager_id>/mandats/<int:mandat_id>/cancel_confirm",
        usagers.usagers_mandats_cancel_confirm,
        name="usagers_mandats_cancel_confirm",
    ),
    # new mandat
    path("creation_mandat/", new_mandat.new_mandat, name="new_mandat"),
    path(
        "creation_mandat/recapitulatif/",
        new_mandat.new_mandat_recap,
        name="new_mandat_recap",
    ),
    path("logout-callback/", new_mandat.new_mandat_recap, name="new_mandat_recap"),
    path(
        "creation_mandat/visualisation/projet/",
        new_mandat.mandat_print_projet,
        name="new_mandat_print_projet",
    ),
    path(
        "creation_mandat/succes/",
        new_mandat.new_mandat_success,
        name="new_mandat_success",
    ),
    path(
        "creation_mandat/visualisation/final/",
        new_mandat.mandat_print_final,
        name="new_mandat_print_final",
    ),
    path(
        "creation_mandat/qrcode/",
        new_mandat.mandat_print_final_qrcode,
        name="new_mandat_print_final_qrcode",
    ),
    # id_provider
    path("authorize/", id_provider.authorize, name="authorize"),
    path("token/", id_provider.token, name="token"),
    path("userinfo/", id_provider.user_info, name="user_info"),
    path("logout/", service.logout_page, name="logout"),
    path("select_demarche/", id_provider.fi_select_demarche, name="fi_select_demarche"),
    # FC_as_FS
    path("fc_authorize/", FC_as_FS.fc_authorize, name="fc_authorize"),
    path("callback/", FC_as_FS.fc_callback, name="fc_callback"),
    # misc
    path("guide_utilisation/", service.guide_utilisation, name="guide_utilisation"),
    path("stats/", service.statistiques, name="statistiques"),
    path("cgu/", service.cgu, name="cgu"),
    path("activity_check/", service.activity_check, name="activity_check"),
    # footer
    path("mentions-legales/", service.mentions_legales, name="mentions_legales"),
]

urlpatterns.extend(magicauth_urls)
