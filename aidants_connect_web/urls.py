from django.urls import path
from aidants_connect_web import views


urlpatterns = [
    path("", views.home_page, name="home_page"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("mandat/", views.mandat, name="mandat"),
    path("recap/", views.recap, name="recap"),
    path("authorize/", views.authorize, name="authorize"),
    path("token/", views.token, name="token"),
    path("userinfo/", views.user_info, name="user_info"),
    path("logout/", views.logout_page, name="logout"),
    path("fc_authorize/", views.fc_authorize, name="fc_authorize"),
    path("callback/", views.fc_callback, name="fc_callback"),
    path("logout-callback/", views.recap, name="recap"),
]
