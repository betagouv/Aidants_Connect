from django.urls import path
from aidants_connect_web import views


urlpatterns = [
    path("", views.home_page, name="home_page"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("franceconnect/", views.france_connect, name="france_connect"),
    path("mandat/", views.mandat, name="mandat"),
    path("recap/", views.recap, name="recap"),
    path("authorize/", views.authorize, name="authorize"),
    path("token/", views.token, name="token"),
    path("userinfo/", views.user_info, name="user_info"),
    path("logout/", views.logout_page, name="logout"),
]
