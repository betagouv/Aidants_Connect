import os
import logging
import jwt
import time
import re
from secrets import token_urlsafe

from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict

from aidants_connect_web.models import Connection, Usager
from aidants_connect_web.forms import UsagerForm


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request, "aidants_connect_web/home_page.html", {"random_string": random_string}
    )


@login_required
def authorize(request):
    fc_callback_url = os.environ["FC_CALLBACK_URL"]

    if request.method == "GET":
        state = request.GET.get("state", False)
        nonce = request.GET.get("nonce", False)
        code = token_urlsafe(64)
        this_connexion = Connection(state=state, code=code, nonce=nonce)
        this_connexion.save()

        if state is False:
            return HttpResponseForbidden()

        return render(
            request,
            "aidants_connect_web/authorize.html",
            {"state": state, "form": UsagerForm()},
        )

    else:
        this_state = request.POST.get("state")
        log.info("post received")
        log.info(request.POST)
        form = UsagerForm(request.POST)
        try:
            that_connection = Connection.objects.get(state=this_state)
            state = that_connection.state
            code = that_connection.code
        except ObjectDoesNotExist:
            log.info(f"No connection corresponds to the state: {this_state}")
            return HttpResponseForbidden()

        if form.is_valid():
            sub = token_urlsafe(64)
            post = form.save(commit=False)

            post.sub = sub
            # post.birthplace
            # post.birthcountry

            post.save()

            that_connection.sub_usager = sub
            that_connection.save()
            # if os.environ["HOST"] == "localhost":
            #     return JsonResponse({"response": "ok"})
            return redirect(f"{fc_callback_url}?code={code}&state={state}")
        else:
            log.info("invalid form")
            return render(
                request,
                "aidants_connect_web/authorize.html",
                {"state": state, "form": form},
            )


# Due to `no_referer` error
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf.csrf_exempt
@csrf_exempt
def token(request):
    fc_client_id = os.environ["FC_AS_FS_ID"]
    fc_client_secret = os.environ["FC_AS_FS_SECRET"]
    host = os.environ["HOST"]

    if request.method == "GET":
        log.info("This method is a get")
        return HttpResponse("You did a GET on a POST only route")

    if request.POST.get("grant_type") != "authorization_code":
        return HttpResponseForbidden()

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
        "sub": connection.sub_usager,
        "nonce": connection.nonce,
    }

    encoded_id_token = jwt.encode(id_token, fc_client_secret, algorithm="HS256")
    access_token = token_urlsafe(64)
    connection.access_token = access_token
    connection.save()
    response = {
        "access_token": access_token,
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

    auth_header = request.META.get('HTTP_AUTHORIZATION')

    if not auth_header:
        log.info("missing auth header")
        return HttpResponseForbidden()

    pattern = re.compile(r'^Bearer\s([A-Z-a-z-0-9-_/-]+)$')
    if not pattern.match(auth_header):
        log.info("Auth header has wrong format")
        return HttpResponseForbidden()

    auth_token = auth_header[7:]
    connection = Connection.objects.get(access_token=auth_token)

    usager = Usager.objects.get(sub=connection.sub_usager)
    usager = model_to_dict(usager)
    del usager["id"]
    birthdate = usager["birthdate"]
    birthplace = usager["birthplace"]
    birthcountry = usager["birthcountry"]
    usager["birthplace"] = str(birthplace)
    usager["birthcountry"] = str(birthcountry)
    usager["birthdate"] = str(birthdate)

    return JsonResponse(usager, safe=False)
