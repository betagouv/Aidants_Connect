from django.urls import path
from aidants_connect_web.views import service, FC_as_FS, id_provider, new_mandat
from magicauth import views as magicauth_views
from magicauth.urls import urlpatterns as magicauth_urls

urlpatterns = [
    # service
    path("", service.home_page, name="home_page"),
    path("accounts/login/", magicauth_views.LoginView.as_view(), name="login"),
    path("dashboard/", service.dashboard, name="dashboard"),
    path("mandats/", service.mandats, name="mandats"),
    # new mandat
    path("new_mandat/", new_mandat.new_mandat, name="new_mandat"),
    path("recap/", new_mandat.recap, name="recap"),
    path("logout-callback/", new_mandat.recap, name="recap"),
    path(
        "generate_mandat_pdf/",
        new_mandat.generate_mandat_pdf,
        name="generate_mandat_pdf",
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
    path("ressources/", service.resources, name="resources"),
]

urlpatterns.extend(magicauth_urls)
