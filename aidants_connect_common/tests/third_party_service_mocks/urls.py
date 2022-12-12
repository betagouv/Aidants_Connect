from django.urls import path

from aidants_connect_common.tests.third_party_service_mocks.views import (
    test_address_api_no_result,
    test_address_api_segur,
    test_sms_api_sms,
    test_sms_api_token,
)

urlpatterns = [
    path(
        "test-address-api/segur/", test_address_api_segur, name="test_address_api_segur"
    ),
    path(
        "test-address-api/no-result/",
        test_address_api_no_result,
        name="test_address_api_no_result",
    ),
    path("test-sms-api/token/", test_sms_api_token, name="test_sms_api_token"),
    path("test-sms-api/sms/", test_sms_api_sms, name="test_sms_api_sms"),
]
