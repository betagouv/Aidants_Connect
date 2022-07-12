from django.http import HttpRequest, HttpResponse

from aidants_connect_habilitation.tests.utils import load_json_fixture


def address_api_segur(request: HttpRequest):
    jsondata = load_json_fixture("segur.json", as_string=True)
    return HttpResponse(jsondata, content_type="application/json")


def address_api_no_result(request: HttpRequest):
    jsondata = load_json_fixture("no_result.json", as_string=True)
    return HttpResponse(jsondata, content_type="application/json")
