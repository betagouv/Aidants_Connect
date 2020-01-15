import jwt
import logging
import re
import time

from secrets import token_urlsafe
from django.http import (
    HttpResponseForbidden,
    HttpResponse,
    JsonResponse,
    HttpResponseBadRequest,
)
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import logout
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
    Journal,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def check_request_parameters(
    parameters: dict, expected_static_parameters: dict, view_name: str
) -> tuple:
    """
    When a request arrives, this function checks that all requested parameters are
    present (if not, returns (1, "missing parameter") and if the static parameters are
    correct (if not, returns (1, "forbidden parameter value")). If all is good, returns
    (0, "all is good")
    :param parameters: dict of all parameters expected in the request
    (None if the parameter was not present)
    :param expected_static_parameters: subset of parameters that are not dynamic
    :param view_name: str with the name of the view for logging purposes
    :return: tuple (error, message) where error is a bool and message an str
    """
    for parameter, value in parameters.items():
        if not value:
            error_message = f"400 Bad request: There is no {parameter} @ {view_name}"
            log.info(error_message)
            return 1, "missing parameter"
        if (
            parameter in expected_static_parameters
            and value != expected_static_parameters[parameter]
        ):
            error_message = (
                f"403 forbidden request: unexpected {parameter} @ {view_name}"
            )
            log.info(error_message)
            return 1, "forbidden parameter value"
    return 0, "all good"


@login_required
def authorize(request):
    if request.method == "GET":
        parameters = {
            "state": request.GET.get("state"),
            "nonce": request.GET.get("nonce"),
            "response_type": request.GET.get("response_type"),
            "client_id": request.GET.get("client_id"),
            "redirect_uri": request.GET.get("redirect_uri"),
            "scope": request.GET.get("scope"),
            "acr_values": request.GET.get("acr_values"),
        }
        expected_static_parameters = {
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            "scope": "openid profile email address phone birth",
            "acr_values": "eidas1",
        }
        error, message = check_request_parameters(
            parameters, expected_static_parameters, "authorize"
        )
        if error:
            return (
                HttpResponseBadRequest()
                if message == "missing parameter"
                else HttpResponseForbidden()
            )

        code = token_urlsafe(64)
        Connection.objects.create(
            state=parameters["state"], code=code, nonce=parameters["nonce"]
        )
        aidant = request.user
        return render(
            request,
            "aidants_connect_web/id_provider/authorize.html",
            {
                "state": parameters["state"],
                "usagers": aidant.get_usagers_with_current_mandat(),
                "aidant": aidant,
            },
        )

    else:
        state = request.POST.get("state")

        try:
            connection = Connection.objects.get(state=state)
            if connection.is_expired:
                log.info("Connexion has expired at authorize")
                return HttpResponseBadRequest()
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the state:")
            log.info(state)
            logout(request)
            return HttpResponseForbidden()
        except Connection.MultipleObjectsReturned:
            log.info("This connection is not unique. State:")
            log.info(state)
            logout(request)
            return HttpResponseForbidden()
        chosen_usager = Usager.objects.get(id=request.POST.get("chosen_usager"))
        if chosen_usager not in request.user.get_usagers_with_current_mandat():
            log.info("This usager does not have a valid mandat with the aidant")
            log.info(request.user.id)
            logout(chosen_usager.id)
            logout(request)
            return HttpResponseForbidden()
        connection.usager = chosen_usager
        connection.save()
        select_demarches_url = f"{reverse('fi_select_demarche')}?state={state}"
        return redirect(select_demarches_url)


@login_required
def fi_select_demarche(request):
    if request.method == "GET":
        state = request.GET.get("state", False)
        usager = Connection.objects.get(state=state).usager
        demarches_rich_text = settings.DEMARCHES
        aidant = request.user
        nom_demarches = aidant.get_current_demarches_for_usager(usager)

        demarches = {
            nom_demarche: demarches_rich_text[nom_demarche]
            for nom_demarche in nom_demarches
        }

        return render(
            request,
            "aidants_connect_web/id_provider/fi_select_demarche.html",
            {
                "state": state,
                "aidant": request.user.get_full_name(),
                "demarches": demarches,
            },
        )
    else:
        this_state = request.POST.get("state")
        try:
            connection = Connection.objects.get(state=this_state)
            if connection.is_expired:
                log.info("Connexion has expired at select demarche")
                return HttpResponseBadRequest()
            code = connection.code
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the state:")
            log.info(this_state)
            logout(request)
            return HttpResponseForbidden()
        except Connection.MultipleObjectsReturned:
            log.info("This connection is not unique. State:")
            log.info(this_state)
            logout(request)
            return HttpResponseForbidden()

        chosen_demarche = request.POST.get("chosen_demarche")
        try:
            chosen_mandat = Mandat.objects.get(
                usager=connection.usager,
                aidant=request.user,
                demarche=chosen_demarche,
                expiration_date__gt=timezone.now(),
            )
        except Mandat.DoesNotExist:
            log.info("The mandat asked does not exist")
            return HttpResponseForbidden()

        connection.demarche = chosen_demarche
        connection.mandat = chosen_mandat
        connection.complete = True
        connection.aidant = request.user
        connection.save()

        fc_callback_url = settings.FC_AS_FI_CALLBACK_URL
        logout(request)
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
        return HttpResponse("You did a GET on a POST only route")

    parameters = {
        "code": request.POST.get("code"),
        "grant_type": request.POST.get("grant_type"),
        "redirect_uri": request.POST.get("redirect_uri"),
        "client_id": request.POST.get("client_id"),
        "client_secret": request.POST.get("client_secret"),
    }
    expected_static_parameters = {
        "grant_type": "authorization_code",
        "redirect_uri": fc_callback_url,
        "client_id": fc_client_id,
        "client_secret": fc_client_secret,
    }

    error, message = check_request_parameters(
        parameters, expected_static_parameters, "token"
    )
    if error:
        return (
            HttpResponseBadRequest()
            if message == "missing parameter"
            else HttpResponseForbidden()
        )

    code = parameters["code"]
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

    usager = model_to_dict(connection.usager)
    del usager["id"]
    birthdate = usager["birthdate"]
    birthplace = usager["birthplace"]
    birthcountry = usager["birthcountry"]
    usager["birthplace"] = str(birthplace)
    usager["birthcountry"] = str(birthcountry)
    usager["birthdate"] = str(birthdate)

    Journal.objects.mandat_use(
        aidant=connection.aidant,
        usager=connection.usager,
        demarche=connection.demarche,
        access_token=connection.access_token,
        mandat=connection.mandat,
    )
    return JsonResponse(usager, safe=False)
