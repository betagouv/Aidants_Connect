from django.urls import path
from aidant_connect_web import views

urlpatterns = [
    path('', views.connection, name='connection')
]
