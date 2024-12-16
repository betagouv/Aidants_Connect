from django.urls import path

from aidants_connect_common.views import (
    FollowMyHabilitationRequestView,
    FormationsInformations,
)

urlpatterns = [
    # service
    path(
        "habilitation-suivre-ma-demande",
        FollowMyHabilitationRequestView.as_view(),
        name="habilitation_follow_my_request",
    ),
    # service
    path(
        "formation/<int:pk>/informations",
        FormationsInformations.as_view(),
        name="formation_informations",
    ),
]
