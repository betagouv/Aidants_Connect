from django.urls import path

from aidants_connect_pico_cms.views import TestimonyView

urlpatterns = [
    path("temoignages/<slug:slug>/", TestimonyView.as_view(), name="temoignage-detail"),
]
