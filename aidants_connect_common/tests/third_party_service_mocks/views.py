import json
from random import randint

from django.conf import settings
from django.core.management.utils import get_random_secret_key
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from requests import post as requests_post

from aidants_connect_common.tests.third_party_service_mocks.utils import (
    load_json_fixture,
)


def test_address_api_segur(request: HttpRequest):
    jsondata = load_json_fixture("segur.json", as_string=True)
    return HttpResponse(jsondata, content_type="application/json")


def test_address_api_no_result(request: HttpRequest):
    jsondata = load_json_fixture("no_result.json", as_string=True)
    return HttpResponse(jsondata, content_type="application/json")


@csrf_exempt
def test_sms_api_token(request: HttpRequest):
    return JsonResponse(
        {
            "access_token": get_random_secret_key(),
            "token_type": "bearer",
            "scope": "api",
            "ttl": 3600,
        }
    )


@csrf_exempt
def test_sms_api_sms(request: HttpRequest):
    data = json.loads(request.body.decode(settings.DEFAULT_CHARSET))

    requests_post(
        request.build_absolute_uri(reverse("sms_callback")),
        json={
            "smsId": str(randint(100_000_000, 999_999_999)),
            "correlationId": data["correlationId"],
            "userId": data["userIds"][0],
            "timeStamp": timezone.now().isoformat(),
            "type": "",
            "mcc": "208",
            "mnc": "14",
            "status": 5,
            "statusMessage": "Delivered to end-user",
            "errorCode": 0,
            "errorMessage": "No further info",
        },
    )

    return JsonResponse(
        {
            "result": [
                {
                    "id": randint(100_000_000, 999_999_999),
                    "userId": data["userIds"][0],
                    "correlationId": data["correlationId"],
                    "status": 0,
                    "statusDetail": "Pending",
                    "type": "SMS",
                }
            ]
        },
        status=201,
    )
