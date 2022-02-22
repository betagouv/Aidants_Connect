import logging
import re
import time
from secrets import token_urlsafe

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt

import jwt

from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.models import Aidant, Connection, Journal, Usager
from aidants_connect_web.utilities import generate_sha256_hash

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
        elif (
            parameter not in expected_static_parameters
            and parameter in ["state", "nonce"]
            and not value.isalnum()
        ):
            error_message = (
                f"403 forbidden request: malformed {parameter} @ {view_name}"
            )
            log.info(error_message)
            return 1, "malformed parameter value"
        elif (
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
@user_is_aidant
@activity_required
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
        EXPECTED_STATIC_PARAMETERS = {
            "response_type": "code",
            "client_id": settings.FC_AS_FI_ID,
            "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
            "scope": "openid profile email address phone birth",
            "acr_values": "eidas1",
        }

        error, message = check_request_parameters(
            parameters, EXPECTED_STATIC_PARAMETERS, "authorize"
        )
        if error:
            return (
                HttpResponseBadRequest()
                if message == "missing parameter"
                else HttpResponseForbidden()
            )

        connection = Connection.objects.create(
            state=parameters["state"],
            nonce=parameters["nonce"],
        )
        aidant = request.user

        return render(
            request,
            "aidants_connect_web/id_provider/authorize.html",
            {
                "connection_id": connection.id,
                "usagers": aidant.get_usagers_with_active_autorisation(),
                "aidant": aidant,
            },
        )

    else:
        parameters = {
            "connection_id": request.POST.get("connection_id"),
            "chosen_usager": request.POST.get("chosen_usager"),
        }

        try:
            connection = Connection.objects.get(pk=parameters["connection_id"])
            if connection.is_expired:
                log.info("connection has expired at authorize")
                return render(request, "408.html", status=408)
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the connection_id:")
            log.info(parameters["connection_id"])
            logout(request)
            return HttpResponseForbidden()

        aidant = request.user
        chosen_usager = Usager.objects.get(pk=parameters["chosen_usager"])
        if chosen_usager not in aidant.get_usagers_with_active_autorisation():
            log.info(
                "This usager does not have a valid autorisation "
                "with the aidant's organisation"
            )
            log.info(aidant.id)
            logout(chosen_usager.id)
            logout(request)
            return HttpResponseForbidden()

        connection.usager = chosen_usager
        connection.save()

        select_demarches_url = (
            f"{reverse('fi_select_demarche')}?connection_id={connection.id}"
        )
        return redirect(select_demarches_url)


@login_required
@user_is_aidant
@activity_required
def fi_select_demarche(request):
    if request.method == "GET":
        parameters = {
            "connection_id": request.GET.get("connection_id"),
        }

        try:
            connection = Connection.objects.get(pk=parameters["connection_id"])
            if connection.is_expired:
                log.info("Connection has expired at select_demarche")
                return render(request, "408.html", status=408)
        except ObjectDoesNotExist:
            log.info("No connection matches the connection_id:")
            log.info(parameters["connection_id"])
            logout(request)
            return HttpResponseForbidden()

        aidant = request.user

        usager_demarches = aidant.get_active_demarches_for_usager(connection.usager)

        demarches = {
            nom_demarche: settings.DEMARCHES[nom_demarche]
            for nom_demarche in usager_demarches
        }

        return render(
            request,
            "aidants_connect_web/id_provider/fi_select_demarche.html",
            {
                "connection_id": connection.id,
                "aidant": request.user.get_full_name(),
                "usager": connection.usager,
                "demarches": demarches,
            },
        )

    else:
        parameters = {
            "connection_id": request.POST.get("connection_id"),
            "chosen_demarche": request.POST.get("chosen_demarche"),
        }

        try:
            connection = Connection.objects.get(pk=parameters["connection_id"])
            if connection.is_expired:
                log.info("connection has expired at select_demarche")
                return render(request, "408.html", status=408)
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the connection_id:")
            log.info(parameters["connection_id"])
            logout(request)
            return HttpResponseForbidden()

        aidant: Aidant = request.user
        autorisation = aidant.get_valid_autorisation(
            parameters["chosen_demarche"], connection.usager
        )
        if not autorisation:
            log.info("The autorisation asked does not exist")
            return HttpResponseForbidden()

        code = token_urlsafe(64)
        connection.code = make_password(code, settings.FC_AS_FI_HASH_SALT)
        connection.demarche = parameters["chosen_demarche"]
        connection.autorisation = autorisation
        connection.complete = True
        connection.aidant = aidant
        connection.organisation = aidant.organisation
        connection.save()

        return redirect(
            f"{settings.FC_AS_FI_CALLBACK_URL}?code={code}&state={connection.state}"
        )


def _mock_refresh_token():
    return get_random_string(18).lower()


# Due to `no_referer` error
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf.csrf_exempt
@csrf_exempt
def token(request):
    if request.method == "GET":
        return HttpResponse("You did a GET on a POST only route")

    client_secret = request.POST.get("client_secret")
    try:
        hash_client_secret = generate_sha256_hash(client_secret.encode())
    except AttributeError:
        return HttpResponseBadRequest()

    parameters = {
        "code": request.POST.get("code"),
        "grant_type": request.POST.get("grant_type"),
        "redirect_uri": request.POST.get("redirect_uri"),
        "client_id": request.POST.get("client_id"),
        "hash_client_secret": hash_client_secret,
    }
    EXPECTED_STATIC_PARAMETERS = {
        "grant_type": "authorization_code",
        "redirect_uri": settings.FC_AS_FI_CALLBACK_URL,
        "client_id": settings.FC_AS_FI_ID,
        "hash_client_secret": settings.HASH_FC_AS_FI_SECRET,
    }

    error, message = check_request_parameters(
        parameters, EXPECTED_STATIC_PARAMETERS, "token"
    )
    if error:
        return (
            HttpResponseBadRequest()
            if message == "missing parameter"
            else HttpResponseForbidden()
        )

    code_hash = make_password(parameters["code"], settings.FC_AS_FI_HASH_SALT)
    try:
        connection = Connection.objects.get(code=code_hash)
        if connection.is_expired:
            log.info("connection has expired at token")
            return render(request, "408.html", status=408)
    except ObjectDoesNotExist:
        log.info("403: /token No connection corresponds to the code")
        log.info(parameters["code"])
        return HttpResponseForbidden()

    id_token = {
        # The audience, the Client ID of your Auth0 Application
        "aud": settings.FC_AS_FI_ID,
        # The expiration time. in the format "seconds since epoch"
        # TODO Check if 10 minutes is not too much
        "exp": int(time.time()) + settings.FC_CONNECTION_AGE,
        # The issued at time
        "iat": int(time.time()),
        # The issuer,  the URL of your Auth0 tenant
        "iss": settings.HOST,
        # The unique identifier of the user
        "sub": connection.usager.sub,
        "nonce": connection.nonce,
    }
    encoded_id_token = jwt.encode(id_token, client_secret, algorithm="HS256")

    access_token = token_urlsafe(64)
    connection.access_token = make_password(access_token, settings.FC_AS_FI_HASH_SALT)
    connection.save()

    response = {
        "access_token": access_token,
        "expires_in": 3600,
        "id_token": encoded_id_token,
        "refresh_token": _mock_refresh_token(),
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
    auth_token_hash = make_password(auth_token, settings.FC_AS_FI_HASH_SALT)
    try:
        connection = Connection.objects.get(access_token=auth_token_hash)
        if connection.is_expired:
            log.info("connection has expired at user_info")
            return render(request, "408.html", status=408)
    except ObjectDoesNotExist:
        log.info("403: /user_info No connection corresponds to the access_token")
        log.info(auth_token)
        return HttpResponseForbidden()

    usager = model_to_dict(
        connection.usager,
        fields=[
            "birthcountry",
            "birthdate",
            "birthplace",
            "creation_date",
            "email",
            "family_name",
            "gender",
            "given_name",
            "preferred_username",
            "sub",
        ],
    )

    birthdate = usager["birthdate"]
    birthplace = usager["birthplace"]
    birthcountry = usager["birthcountry"]
    usager["birthplace"] = str(birthplace)
    usager["birthcountry"] = str(birthcountry)
    usager["birthdate"] = str(birthdate)

    Journal.log_autorisation_use(
        aidant=connection.aidant,
        usager=connection.usager,
        demarche=connection.demarche,
        access_token=connection.access_token,
        autorisation=connection.autorisation,
    )

    return JsonResponse(usager, safe=False)


def end_session_endpoint(request):
    if request.method != "GET":
        log.info("Request should be a GET @ end_session_endpoint")
        return HttpResponseBadRequest()

    redirect_uri = settings.FC_AS_FI_LOGOUT_REDIRECT_URI
    if request.GET.get("post_logout_redirect_uri") != redirect_uri:
        message = (
            f"post_logout_redirect_uri is "
            f"{request.GET.get('post_logout_redirect_uri')} instead of "
            f"{redirect_uri} @ end_session_endpoint"
        )
        log.info(message)
        return HttpResponseBadRequest()

    return HttpResponseRedirect(redirect_uri)
