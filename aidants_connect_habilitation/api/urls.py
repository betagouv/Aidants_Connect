from django.urls import path

from aidants_connect_habilitation.api.views import PersonnelRequestEditView

urlpatterns = [
    path(
        "demandeur/<str:issuer_id>/organisation/<str:uuid>/aidant/<int:aidant_id>/edit/",  # noqa: E501
        PersonnelRequestEditView.as_view(),
        name="api_habilitation_aidant_edit",
    ),
]
