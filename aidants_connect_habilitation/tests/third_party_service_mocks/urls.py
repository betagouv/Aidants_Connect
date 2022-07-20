from django.urls import path

from aidants_connect_habilitation.tests.third_party_service_mocks.views import (
    address_api_no_result,
    address_api_segur,
)

urlpatterns = [
    path("address-api/segur/", address_api_segur, name="address_api_segur"),
    path("address-api/no-result/", address_api_no_result, name="address_api_no_result"),
]
