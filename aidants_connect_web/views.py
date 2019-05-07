import os
import logging
from secrets import token_urlsafe
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist

from aidants_connect_web.models import Connection


fc_callback_url = os.getenv("FC_CALLBACK_URL")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def home_page(request):
    return render(request, "aidants_connect_web/home_page.html")


@login_required
def authorize(request):
    if request.method == "GET":
        state = request.GET.get("state", False)
        nonce = request.GET.get("nonce", False)
        code = token_urlsafe(64)
        this_connexion = Connection(state=state, code=code, nonce=nonce)
        this_connexion.save()
        try:
            log.info(f"this is all the connections one: {Connection.objects.all()}")
        except ObjectDoesNotExist:
            log.info("This connection does not exist")
        log.info("this is the starting state", state)
        if state is False:
            return HttpResponseForbidden()

        return render(request, "aidants_connect_web/authorize.html", {"state": state})

    else:
        user_info = request.POST.get("user_info")
        this_state = request.POST.get("state")

        try:
            that_connection = Connection.objects.get(state=this_state)
            state = that_connection.state
            code = that_connection.code
        except ObjectDoesNotExist:
            log.info(f"No connection corresponds to the state: {this_state}")
            return HttpResponseForbidden()

        if user_info == "good":
            log.debug(
                "the URI it redirects to",
                f"{fc_callback_url}?code={code}&state={state}",
            )
            return redirect(
                f"{fc_callback_url}?code={code}&state={state}"
            )
        else:
            return HttpResponseForbidden()


# Due to `no_referer` error
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf.csrf_exempt
@csrf_exempt
def token(request):
    if request.method == "GET":
        log.info("This method is a get")

        return HttpResponse("You did a GET on a POST only route")
    log.info("sending token payload")

    id_token = {
        'aud': '895fae591ccae777094931e269e46447',
        'exp':1412953984,
        'iat': 1412950384,
        'iss':'http://impots-franceconnect.fr',
        'sub': 4344343423,
        'nonce': 34324432468
        }
    response = {
        "access_token": "N5ro73Y2UBpVYLc8xB137A",
        "expires_in": 3600,
        "id_token": "irX5DyZU5P1MNP6vj4b5gQ",
        "refresh_token": "5ieq7Bg173y99tT6MA",
        "token_type": "Bearer",
    }

    definite_response = JsonResponse(response)

    return definite_response


def user_info(request):
    # Entêtes
    # HTTP: Authorization = 'Bearer <ACCESS_TOKEN>'
    # <FI_URL>/api/user?schema=openid
    response = {
        "given_name": "Joséphine",
        "family_name": "ST-PIERRE",
        "preferred_username": "ST-PIERRE",
        "birthdate": "1969-12-15",
        "gender": "F",
        "birthplace": "70447",
        "birthcountry": "99100",
    }
    return JsonResponse(response)
