from django.urls import path
from aidant_connect_web import views

urlpatterns = [
    path("", views.connection, name="connection"),
    path("fc_authorize/<str:role>/", views.fc_authorize, name="fc_authorize"),
    path("callback/", views.fc_callback, name="fc_callback"),
    path("switchboard/", views.switchboard, name="switchboard"),
    path("logout-callback", views.logout_callback, name="logout_callback"),
]
