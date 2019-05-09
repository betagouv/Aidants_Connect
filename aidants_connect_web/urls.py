from django.urls import path
from aidants_connect_web import views


urlpatterns = [
    path("", views.home_page, name="home_page"),
    path("authorize/", views.authorize, name="authorize"),
    path("token/", views.token, name="token"),
]
