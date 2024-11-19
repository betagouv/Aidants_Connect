from django.urls import path

from rest_framework import routers

from aidants_connect_web.api.views import (
    NewHabilitationRequestSubmitNew,
    NewHabilitationRequestSubmitNewEdit,
    OrganisationViewSet,
)

router = routers.DefaultRouter()
router.register(r"organisations", OrganisationViewSet)

urlpatterns = [
    path(
        "espace-responsable/aidant/habiliter/",
        NewHabilitationRequestSubmitNew.as_view(),
        name="api_espace_responsable_aidant_new",
    ),
    path(
        "espace-responsable/aidant/habiliter/editer/<int:idx>/",
        NewHabilitationRequestSubmitNewEdit.as_view(),
        name="api_espace_responsable_aidant_new_edit",
    ),
]
