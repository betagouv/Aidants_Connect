import jwt
import logging
import re
import time

from secrets import token_urlsafe
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from django.utils import timezone
from django.urls import reverse
from django.shortcuts import render, redirect
from django.conf import settings
from aidants_connect_web.models import (
    Connection,
    Mandat,
    Usager,
    CONNECTION_EXPIRATION_TIME,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
def authorize(request):
    if request.method == "GET":
        state = request.GET.get("state", False)
        nonce = request.GET.get("nonce", False)
        code = token_urlsafe(64)
        this_connexion = Connection(state=state, code=code, nonce=nonce)
        this_connexion.save()
        if state is False:
            log.info("403: There is no state")
            return HttpResponseForbidden()

        aidant = request.user
        mandats_for_aidant = Mandat.objects.filter(aidant=aidant)
        usagers_id = mandats_for_aidant.values_list("usager", flat=True)
        # TODO Do we send the whole usager ? or only first name and last name and id ?
        usagers = [Usager.objects.get(id=usager_id) for usager_id in usagers_id]

        return render(
            request,
            "aidants_connect_web/id_provider/authorize.html",
            {"state": state, "usagers": usagers, "aidant": aidant},
        )

    else:
        this_state = request.POST.get("state")
        try:
            that_connection = Connection.objects.get(state=this_state)
            state = that_connection.state

        except ObjectDoesNotExist:
            log.info("No connection corresponds to the state:")
            log.info(this_state)
            return HttpResponseForbidden()
        except Connection.MultipleObjectsReturned:
            log.info("This connection is not unique. State:")
            log.info(this_state)
            return HttpResponseForbidden()

        # TODO check if connection has not expired

        that_connection.usager = Usager.objects.get(
            id=request.POST.get("chosen_usager")
        )
        that_connection.save()
        select_demarches_url = f"{reverse('fi_select_demarche')}?state={state}"
        return redirect(select_demarches_url)


@login_required
def fi_select_demarche(request):

    if request.method == "GET":
        state = request.GET.get("state", False)
        usager = Connection.objects.get(state=state).usager
        # TODO for Usager, should we use sub_usager or internal ID ?
        # TODO Should we have different instances of the same usager for each aidant
        #  ? for each mandat ? at all ?
        # the [Ø] in the following line is in case the same user has several mandat
        mandats = Mandat.objects.filter(usager=usager, aidant=request.user)

        demarches_per_mandat = mandats.values_list("perimeter", flat=True)

        demarches = set(
            [demarche for sublist in demarches_per_mandat for demarche in sublist]
        )

        return render(
            request,
            "aidants_connect_web/id_provider/fi_select_demarche.html",
            {"state": state, "demarches": demarches, "aidant": request.user.first_name},
        )
    else:
        this_state = request.POST.get("state")
        try:
            that_connection = Connection.objects.get(state=this_state)
            code = that_connection.code
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the state:")
            log.info(this_state)
            return HttpResponseForbidden()
        except Connection.MultipleObjectsReturned:
            log.info("This connection is not unique. State:")
            log.info(this_state)
            return HttpResponseForbidden()

        # TODO check if connection has not expired
        that_connection.demarche = request.POST.get("chosen_demarche")
        that_connection.complete = True
        that_connection.save()

        fc_callback_url = settings.FC_AS_FI_CALLBACK_URL
        return redirect(f"{fc_callback_url}?code={code}&state={this_state}")


# Due to `no_referer` error
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf.csrf_exempt
@csrf_exempt
def token(request):
    fc_callback_url = settings.FC_AS_FI_CALLBACK_URL
    fc_client_id = settings.FC_AS_FI_ID
    fc_client_secret = settings.FC_AS_FI_SECRET
    host = settings.HOST

    if request.method == "GET":
        log.info("This method is a get")
        return HttpResponse("You did a GET on a POST only route")

    rules = [
        request.POST.get("grant_type") == "authorization_code",
        request.POST.get("redirect_uri") == fc_callback_url,
        request.POST.get("client_id") == fc_client_id,
        request.POST.get("client_secret") == fc_client_secret,
    ]
    if not all(rules):
        log.info("403: Rules are not all abided")
        log.info(rules)
        return HttpResponseForbidden()

    code = request.POST.get("code")

    try:
        connection = Connection.objects.get(code=code)
    except ObjectDoesNotExist:
        log.info("403: /token No connection corresponds to the code")
        log.info(code)
        return HttpResponseForbidden()

    if connection.expiresOn < timezone.now():
        log.info("403: Code expired")
        return HttpResponseForbidden()
    id_token = {
        # The audience, the Client ID of your Auth0 Application
        "aud": fc_client_id,
        # The expiration time. in the format "seconds since epoch"
        # TODO Check if 10 minutes is not too much
        "exp": int(time.time()) + CONNECTION_EXPIRATION_TIME * 60,
        # The issued at time
        "iat": int(time.time()),
        # The issuer,  the URL of your Auth0 tenant
        "iss": host,
        # The unique identifier of the user
        "sub": connection.usager.sub,
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

    definite_response = JsonResponse(response)
    return definite_response


def user_info(request):

    auth_header = request.META.get("HTTP_AUTHORIZATION")

    if not auth_header:
        log.info("403: Missing auth header")
        return HttpResponseForbidden()

    pattern = re.compile(r"^Bearer\s([A-Z-a-z-0-9-_/-]+)$")
    if not pattern.match(auth_header):
        log.info("Auth header has wrong format")
        return HttpResponseForbidden()

    auth_token = auth_header[7:]
    connection = Connection.objects.get(access_token=auth_token)

    if connection.expiresOn < timezone.now():
        return HttpResponseForbidden()
    # TODO decide how to deal with user having several mandats/aidants
    usager = model_to_dict(connection.usager)
    del usager["id"]
    birthdate = usager["birthdate"]
    birthplace = usager["birthplace"]
    birthcountry = usager["birthcountry"]
    usager["birthplace"] = str(birthplace)
    usager["birthcountry"] = str(birthcountry)
    usager["birthdate"] = str(birthdate)

    return JsonResponse(usager, safe=False)
