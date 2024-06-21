from django.urls import path

from aidants_connect_common.views import FollowMyHabilitationRequestView

urlpatterns = [
    # service
    path(
        "habilitation-suivre-ma-demande",
        FollowMyHabilitationRequestView.as_view(),
        name="habilitation_follow_my_request",
    ),
]
