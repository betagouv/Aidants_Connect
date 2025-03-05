from django.conf import settings
from django.urls import path

from rest_framework import routers

from aidants_connect_web.api.views import (
    FNEAidantViewSet,
    FNEOrganisationViewSet,
    NewHabilitationRequestSubmitNew,
    NewHabilitationRequestSubmitNewEdit,
    OrganisationViewSet,
)

router = routers.DefaultRouter()
router.register(r"organisations", OrganisationViewSet)
router.register(
    f"{settings.URL_FNEAPI}/fne_aidants", FNEAidantViewSet, basename="fne_aidants"
)
router.register(
    f"{settings.URL_FNEAPI}/fne_organisations",
    FNEOrganisationViewSet,
    basename="fne_organisations",
)
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
