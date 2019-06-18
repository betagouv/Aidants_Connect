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
from django.conf import settings
from django.utils import timezone

from aidants_connect_web.models import (
    Connection,
    User,
    Usager,
    CONNECTION_EXPIRATION_TIME,
)
from aidants_connect_web.forms import UsagerForm, MandatForm


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request, "aidants_connect_web/home_page.html", {"random_string": random_string}
    )


@login_required
def dashboard(request):
    user = User.objects.get(id=request.user.id)
    usagers = Usager.objects.select_related("mandat")
    return render(
        request, "aidants_connect_web/dashboard.html", {"user": user, "usager": usagers}
    )


@login_required
def france_connect(request):
    user = User.objects.get(id=request.user.id)
    return render(
        request,
        "aidants_connect_web/mandat/france_connect.html",
        {"user": user, "form": MandatForm()},
    )


@login_required
def mandat(request):
    user = User.objects.get(id=request.user.id)

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/mandat/mandat.html",
            {"user": user, "form": MandatForm()},
        )

    else:
        usagers = [{"given_name": "George", "family_name": "Abitbol"}]
        return render(
            request,
            "aidants_connect_web/dashboard.html",
            {"user": user, "usagers": usagers},
        )


@login_required
def authorize(request):
    fc_callback_url = settings.FC_CALLBACK_URL
    log.info(fc_callback_url)

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
        form = UsagerForm(request.POST)
        try:
            that_connection = Connection.objects.get(state=this_state)
            state = that_connection.state
            code = that_connection.code
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the state:")
            log.info(this_state)
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
    fc_callback_url = settings.FC_CALLBACK_URL
    fc_client_id = settings.FC_AS_FS_ID
    fc_client_secret = settings.FC_AS_FS_SECRET
    host = settings.HOST

    if request.method == "GET":
        log.info("This method is a get")
        return HttpResponse("You did a GET on a POST only route")

    rules = [
        request.POST.get("grant_type") == "authorization_code",
        request.POST.get("redirect_uri") == f"{fc_callback_url}/oidc_callback",
        request.POST.get("client_id") == fc_client_id,
        request.POST.get("client_secret") == fc_client_secret,
    ]
    if not all(rules):
        return HttpResponseForbidden()

    code = request.POST.get("code")

    try:
        connection = Connection.objects.get(code=code)
    except ObjectDoesNotExist:
        log.info("/token No connection corresponds to the code")
        log.info(code)
        return HttpResponseForbidden()

    if connection.expiresOn < timezone.now():
        log.info("Code expired")
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
        "sub": connection.sub_usager,
        "nonce": connection.nonce,
    }

    encoded_id_token = jwt.encode(id_token, fc_client_secret, algorithm="HS256")
    log.info(encoded_id_token.decode("utf-8"))
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
        log.info("missing auth header")
        return HttpResponseForbidden()

    pattern = re.compile(r"^Bearer\s([A-Z-a-z-0-9-_/-]+)$")
    if not pattern.match(auth_header):
        log.info("Auth header has wrong format")
        return HttpResponseForbidden()

    auth_token = auth_header[7:]
    connection = Connection.objects.get(access_token=auth_token)

    if connection.expiresOn < timezone.now():
        return HttpResponseForbidden()
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


def fc_authorize(request, role="aidant"):

    if role == "aidant":
        redirect_url = "/switchboard/"
    elif role == "usager":
        redirect_url = "/identite_pivot/"
    else:
        raise Http404(f"{role} is not a compatible role")

    state = token_urlsafe(16)
    connexion = Connection(state=state, redirectUrl=redirect_url)
    connexion.save()

    log.info("setting fc state")
    log.info(state)
    fc_nonce = "customNonce11"
    # The nounce is fixed for now as it doesn't seem to be used anywhere else.

    fc_scopes = [
        "given_name",
        "family_name",
        "preferred_username",
        "birthdate",
        "gender",
        "birthplace",
        "birthcountry",
    ]

    parameters = (
        f"response_type=code"
        f"&client_id={fc_id}"
        f"&redirect_uri={fc_callback_uri}"
        f"&scope={'openid' + ''.join(['%20' + scope for scope in fc_scopes])}"
        f"&state={state}"
        f"&nonce={fc_nonce}"
    )

    authorize_url = f"{fc_base}/authorize?{parameters}"
    log.info("auth url")
    log.info(authorize_url)
    return redirect(authorize_url)


def fc_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")

    try:
        connection_state = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        log.info("checking connection db")
        log.info(Connection.objects.all())
        log.info(state)
        connection_state = None

    log.info("Getting state after callback")
    log.info(connection_state)

    if not connection_state:
        return HttpResponseForbidden()
    if connection_state.expiresOn < timezone.now():
        return HttpResponseForbidden()

    token_url = f"{fc_base}/token"
    payload = {
        "grant_type": "authorization_code",
        "redirect_uri": fc_callback_uri,
        "client_id": fc_id,
        "client_secret": fc_secret,
        "code": code,
    }

    headers = {"Accept": "application/json"}
    request_for_token = python_request.post(token_url, data=payload, headers=headers)
    content = request_for_token.json()

    log.info("fc_token_content")
    log.info(content)
    fc_access_token = content.get("access_token")

    fc_id_token = content.get("id_token")
    log.info("fc_id_token")
    log.info(fc_id_token)
    # TODO understand why id_token is a string and not an object

    request.session["user_info"] = python_request.get(
        f"{fc_base}/userinfo?schema=openid",
        headers={"Authorization": f"Bearer {fc_access_token}"},
    ).json()

    logout_base = f"{fc_base}/logout"
    logout_id_token = f"id_token_hint={fc_id_token}"
    logout_state = f"state={state}"
    logout_redirect = f"post_logout_redirect_uri=http://localhost:1337/logout-callback"
    logout_url = f"{logout_base}?{logout_id_token}&{logout_state}&{logout_redirect}"
    log.info("logout redirect")
    log.info(logout_url)

    return redirect(logout_url)


def logout_callback(request):
    state = request.GET.get("state")

    try:
        this_connection = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        log.info("checking connection db")
        log.info(connections=Connection.objects.all())
        log.info(state)
        this_connection = None

    log.info("Getting state after logout_callback")
    log.info(this_connection)
    if not this_connection:
        return HttpResponseForbidden()

    return redirect(this_connection.redirectUrl)


def switchboard(request):

    user_info = request.session.get("user_info")

    if user_info is None:
        return render(request, "aidant_connect_web/connection.html")

    return render(
        request, "aidant_connect_web/switchboard.html", {"user_info": user_info}
    )


def identite_pivot(request):
    id = request.session["user_info"]
    # phrase = "{" + ", ".join([key + ": " + value for key, value in id.items()]) + "}"

    return JsonResponse(id)
