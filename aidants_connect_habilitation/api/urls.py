from django.urls import path

from aidants_connect_habilitation.api.views import (
    PersonnelRequestEditView,
    PersonnelRequestView,
    PersonnelRequestViewIdx,
)

urlpatterns = [
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidant/<int:aidant_id>/modify/",  # noqa: E501
        PersonnelRequestEditView.as_view(),
        name="api_habilitation_aidant_edit",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidants/",
        PersonnelRequestView.as_view(empty_permitted=False),
        name="api_habilitation_new_aidants",
    ),
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidants/<int:idx>/",
        PersonnelRequestViewIdx.as_view(),
        name="api_habilitation_new_aidants_idx",
    ),
]
