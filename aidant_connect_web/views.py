import os
import structlog
import requests as python_request
from secrets import token_urlsafe

from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden, Http404, JsonResponse
from aidant_connect_web.models import Connection

fc_base = os.getenv("FRANCE_CONNECT_URL")
current_host = os.getenv("HOST")
fc_callback_uri = f"{current_host}/callback"

fc_id = os.getenv("FC_ID")
fc_secret = os.getenv("FC_SECRET")

log = structlog.get_logger()


def connection(request):
    return render(request, "aidant_connect_web/connection.html")


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

    log.msg("setting fc state", state=state)
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
    log.msg("auth url", url=authorize_url)
    return redirect(authorize_url)


def fc_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")

    try:
        connection_state = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        log.msg(
            "checking connection db", connections=Connection.objects.all(), state=state
        )
        connection_state = None

    log.msg("Getting state after callback", connection_state=connection_state)

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

    log.msg("fc_token_content", content=content)
    fc_access_token = content.get("access_token")

    fc_id_token = content.get("id_token")
    log.msg("fc_id_token", fc_id_token=fc_id_token)
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
    log.msg("logout redirect", url=logout_url)

    return redirect(logout_url)


def logout_callback(request):
    state = request.GET.get("state")

    try:
        this_connection = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        log.msg(
            "checking connection db", connections=Connection.objects.all(), state=state
        )
        this_connection = None

    log.msg("Getting state after logout_callback", connection_state=this_connection)
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
