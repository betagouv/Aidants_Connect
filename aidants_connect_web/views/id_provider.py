import logging
import re
import time
from secrets import token_urlsafe
from urllib.parse import urlencode

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
from django.views.generic import FormView

import jwt

from aidants_connect_common.forms import PatchedErrorList
from aidants_connect_web.decorators import (
    activity_required,
    aidant_logged_with_activity_required,
    user_is_aidant,
)
from aidants_connect_web.forms import AuthorizeSelectUsagerForm, OAuthParametersForm
from aidants_connect_web.models import Aidant, Connection, Journal, UsagerQuerySet
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


@aidant_logged_with_activity_required
class Authorize(FormView):
    form_class = AuthorizeSelectUsagerForm
    template_name = "aidants_connect_web/id_provider/authorize.html"

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        self.usager_with_active_auth: UsagerQuerySet = (
            self.aidant.get_usagers_with_active_autorisation()
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = OAuthParametersForm(data=request.GET)
        if form.is_valid():
            self.oauth_parameters_form = form
            self.connection = Connection.objects.create(
                state=form.cleaned_data["state"], nonce=form.cleaned_data["nonce"]
            )
            return super().get(request, *args, **kwargs)
        else:
            return self.form_invalid_get(form)

    def form_invalid(self, form):
        connection_errors = form.errors.get("connection_id", PatchedErrorList())
        if "connection_error" in connection_errors.error_codes:
            log.info(
                "No connection corresponds to the connection_id: "
                f"{self.request.POST.get('connection_id')}"
            )
            logout(self.request)
            return HttpResponseForbidden()

        if "connection_expired" in connection_errors.error_codes:
            log.info("connection has expired at authorize")
            return render(self.request, "408.html", status=408)

        if not form.cleaned_data.get("chosen_usager"):
            log.info(
                f"User {self.request.POST['chosen_usager']} does not have a valid "
                f"autorisation with the organisation of aidant with id {self.aidant.id}"
            )
            logout(self.request)
            return HttpResponseForbidden()

        return super().form_invalid(form)

    def form_valid(self, form):
        self.oauth_parameters_form = OAuthParametersForm(
            data=self.request.POST, relaxed=True
        )

        if not self.oauth_parameters_form.is_valid():
            # That case should only happen if, for whatever reason,
            # the user touched the HTML with their sticky fingers…
            log.error(
                "The HTML was modified, bad OAuth parameters "
                f"{self.oauth_parameters_form.data!r}"
            )
            # Punish the user
            logout(self.request)
            return HttpResponseForbidden()

        self.connection = form.cleaned_data["connection_id"]
        self.connection.usager = form.cleaned_data["chosen_usager"]
        self.connection.save()
        return super().form_valid(form)

    def form_invalid_get(self, form):
        view_location = f"{self.__module__}.{self.__class__.__name__}"
        requirement_errors = set()
        format_validation_errors = set()
        additionnal_keys_errors = set()
        for field_name, errors in form.errors.items():
            if "required" in errors.error_codes:
                requirement_errors.update([field_name])
            if "invalid" in errors.error_codes:
                requirement_errors.update([field_name])
            if error := errors.get_error_by_code("additionnal_key"):
                additionnal_keys_errors.update([error.message])

        if requirement_errors:
            log.info(
                f"400 Bad request: The following parameters are missing: "
                f"{requirement_errors!r} @ {view_location}"
            )
            return HttpResponseBadRequest("missing parameter")

        if format_validation_errors:
            log.info(
                "403 forbidden request: The following parameters are malformed: "
                f"{format_validation_errors!r} @ {view_location}"
            )
            return HttpResponseForbidden("malformed parameter value")

        if additionnal_keys_errors:
            log.info(
                "403 forbidden request: Unexpected parameters: "
                f"{additionnal_keys_errors!r} @ {view_location}"
            )
            return HttpResponseForbidden("forbidden parameter value")

        log.warning(f"Uncatched validation error @ {view_location}")
        return HttpResponseBadRequest()

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "usager_with_active_auth": self.usager_with_active_auth,
        }

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "oauth_parameters_form": self.oauth_parameters_form,
            "connection_id": self.connection.id,
            "usagers": self.usager_with_active_auth,
            "aidant": self.aidant,
            "data": [
                {"value": user.id, "label": user.get_full_name()}
                for user in self.usager_with_active_auth
            ],
        }

    def get_success_url(self):
        parameters = urlencode(
            {
                **self.oauth_parameters_form.cleaned_data,
                "connection_id": self.connection.id,
            },
        )
        return f"{reverse('fi_select_demarche')}?{parameters}"


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

        aidant: Aidant = request.user

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
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf
# .csrf_exempt
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
        "exp": int(time.time()) + settings.FC_CONNECTION_AGE,  # The issued at time
        "iat": int(time.time()),  # The issuer,  the URL of your Auth0 tenant
        "iss": settings.HOST,  # The unique identifier of the user
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
