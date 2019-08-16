from django.urls import path
from aidants_connect_web.views import service, FC_as_FS, id_provider


urlpatterns = [
    # service
    path("", service.home_page, name="home_page"),
    path("dashboard/", service.dashboard, name="dashboard"),
    path("mandats/", service.mandats, name="mandats"),
    # new mandat
    path("new_mandat/", service.new_mandat, name="new_mandat"),
    path("recap/", service.recap, name="recap"),
    path("logout-callback/", service.recap, name="recap"),
    path(
        "generate_mandat_pdf/", service.generate_mandat_pdf, name="generate_mandat_pdf"
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
]
