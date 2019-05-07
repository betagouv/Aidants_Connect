import os
import logging
import jwt
import time
from secrets import token_urlsafe

from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist

from aidants_connect_web.models import Connection


fc_callback_url = os.getenv("FC_CALLBACK_URL")
fc_client_id = os.getenv("FC_AS_FS_ID")
fc_client_secret = os.getenv("FC_AS_FS_SECRET")
host = os.getenv("HOST")
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
            return redirect(f"{fc_callback_url}?code={code}&state={state}")
        else:
            return HttpResponseForbidden()


# Due to `no_referer` error
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf.csrf_exempt
@csrf_exempt
def token(request):
    if request.method == "GET":
        log.info("This method is a get")
        return HttpResponse("You did a GET on a POST only route")

    code = request.POST.get("code")
    log.info("the code is")
    log.info(code)
    try:
        connection = Connection.objects.get(code=code)
    except ObjectDoesNotExist:
        log.info(f"/token No connection corresponds to the code")
        log.info(code)
        return HttpResponseForbidden()

    id_token = {
        # The audience, the Client ID of your Auth0 Application
        "aud": fc_client_id,
        # The expiration time. in the format "seconds since epoch"
        # TODO Check if 10 minutes is not too much
        "exp": int(time.time()) + 600,
        # The issued at time
        "iat": int(time.time()),
        # The issuer,  the URL of your Auth0 tenant
        "iss": host,
        # The unique identifier of the user
        "sub": "4344343423",
        "nonce": connection.nonce,
    }
    log.info("type du client secret")
    log.info(type(fc_client_secret))
    encoded_id_token = jwt.encode(id_token, fc_client_secret, algorithm="HS256")

    response = {
        "access_token": "N5ro73Y2UBpVYLc8xB137A",
        "expires_in": 3600,
        "id_token": encoded_id_token.decode("utf-8"),
        "refresh_token": "5ieq7Bg173y99tT6MA",
        "token_type": "Bearer",
    }
    log.info(f"/token id_token:")
    log.info(id_token)
    definite_response = JsonResponse(response)
    log.info("sending token payload")
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
