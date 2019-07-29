import logging
import jwt
import requests as python_request
from secrets import token_urlsafe

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone

from aidants_connect_web.models import Connection

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def fc_authorize(request):
    fc_base = settings.FC_AS_FS_BASE_URL
    fc_id = settings.FC_AS_FS_ID
    fc_callback_uri = f"{settings.FC_AS_FS_CALLBACK_URL}/callback"

    state = token_urlsafe(16)
    fc_nonce = token_urlsafe(16)
    connexion = Connection(state=state, connection_type="FS", nonce=fc_nonce)
    connexion.save()

    fc_scopes = [
        "given_name",
        "family_name",
        "preferred_username",
        "birthdate",
        "gender",
        "birthplace",
        "birthcountry",
        "email"
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

    return redirect(authorize_url)


def fc_callback(request):
    fc_base = settings.FC_AS_FS_BASE_URL
    fc_callback_uri = f"{settings.FC_AS_FS_CALLBACK_URL}/callback"
    fc_callback_uri_logout = f"{settings.FC_AS_FS_CALLBACK_URL}/logout-callback"
    fc_id = settings.FC_AS_FS_ID
    fc_secret = settings.FC_AS_FS_SECRET

    code = request.GET.get("code")
    state = request.GET.get("state")

    try:
        connection_state = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        log.info("FC as FS - This state does not seem to exist")
        log.info(Connection.objects.all())
        log.info(state)
        connection_state = None

    if not connection_state:
        log.info("403: No connection available with this state.")
        return HttpResponseForbidden()

    if connection_state.expiresOn < timezone.now():
        log.info("403: The connection has expired.")
        return HttpResponseForbidden()
    if not code:
        log.info("403: No code has been provided.")
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
    fc_access_token = content.get("access_token")

    fc_id_token = content.get("id_token")
    decoded_token = jwt.decode(
        fc_id_token,
        settings.FC_AS_FS_SECRET,
        audience=settings.FC_AS_FS_ID,
        algorithm="HS256",
    )
    if connection_state.nonce != decoded_token.get("nonce"):
        log.info("403: The nonce is different than the one expected.")
        return HttpResponseForbidden()
    if connection_state.expiresOn < timezone.now():
        log.info("403: The connection has expired.")
        return HttpResponseForbidden()

    request.session["usager"] = python_request.get(
        f"{fc_base}/userinfo?schema=openid",
        headers={"Authorization": f"Bearer {fc_access_token}"},
    ).json()

    logout_base = f"{fc_base}/logout"
    logout_id_token = f"id_token_hint={fc_id_token}"
    logout_state = f"state={state}"
    logout_redirect = f"post_logout_redirect_uri={fc_callback_uri_logout}"
    logout_url = f"{logout_base}?{logout_id_token}&{logout_state}&{logout_redirect}"

    return redirect(logout_url)
