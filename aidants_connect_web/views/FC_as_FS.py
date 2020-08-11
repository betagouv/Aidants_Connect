import logging
from secrets import token_urlsafe
import jwt
from jwt.api_jwt import ExpiredSignatureError
import requests as python_request

from django.conf import settings
from django.contrib import messages as django_messages
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from aidants_connect_web.models import Connection, Usager, Journal
from aidants_connect_web.utilities import generate_sha256_hash


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def fc_authorize(request):
    connection = Connection.objects.get(pk=request.session["connection"])

    connection.state = token_urlsafe(16)
    connection.nonce = token_urlsafe(16)
    connection.connection_type = "FS"
    connection.save()

    fc_base = settings.FC_AS_FS_BASE_URL
    fc_id = settings.FC_AS_FS_ID
    fc_callback_uri = f"{settings.FC_AS_FS_CALLBACK_URL}/callback"
    fc_scopes = [
        "email",
        "gender",
        "birthdate",
        "birthplace",
        "given_name",
        "family_name",
        "birthcountry",
    ]

    parameters = (
        f"response_type=code"
        f"&client_id={fc_id}"
        f"&redirect_uri={fc_callback_uri}"
        f"&scope={'openid' + ''.join(['%20' + scope for scope in fc_scopes])}"
        f"&state={connection.state}"
        f"&nonce={connection.nonce}"
        f"&acr_values=eidas1"
    )

    authorize_url = f"{fc_base}/authorize?{parameters}"

    return redirect(authorize_url)


def fc_callback(request):
    fc_base = settings.FC_AS_FS_BASE_URL
    fc_callback_uri = f"{settings.FC_AS_FS_CALLBACK_URL}/callback"
    fc_callback_uri_logout = f"{settings.FC_AS_FS_CALLBACK_URL}/logout-callback"
    fc_id = settings.FC_AS_FS_ID
    fc_secret = settings.FC_AS_FS_SECRET
    state = request.GET.get("state")

    try:
        connection = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        log.info("FC as FS - This state does not seem to exist")
        log.info(state)
        return HttpResponseForbidden()

    if connection.is_expired:
        log.info("408: FC connection has expired.")
        return render(request, "408.html", status=408)

    code = request.GET.get("code")
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
    connection.access_token = content.get("access_token")
    connection.save()
    fc_id_token = content.get("id_token")

    try:
        decoded_token = jwt.decode(
            fc_id_token,
            settings.FC_AS_FS_SECRET,
            audience=settings.FC_AS_FS_ID,
            algorithm="HS256",
        )
    except ExpiredSignatureError:
        log.info("403: token signature has expired.")
        return HttpResponseForbidden()

    if connection.nonce != decoded_token.get("nonce"):
        log.info("403: The nonce is different than the one expected.")
        return HttpResponseForbidden()

    if connection.is_expired:
        log.info("408: FC connection has expired.")
        return render(request, "408.html", status=408)

    usager, error = get_user_info(connection)
    if error:
        django_messages.error(request, error)
        return redirect("espace_aidant_home")

    connection.usager = usager
    connection.save()

    Journal.log_franceconnection_usager(
        aidant=connection.aidant, usager=connection.usager,
    )

    logout_base = f"{fc_base}/logout"
    logout_id_token = f"id_token_hint={fc_id_token}"
    logout_state = f"state={state}"
    logout_redirect = f"post_logout_redirect_uri={fc_callback_uri_logout}"
    logout_url = f"{logout_base}?{logout_id_token}&{logout_state}&{logout_redirect}"
    return redirect(logout_url)


def get_user_info(connection: Connection) -> tuple:
    fc_base = settings.FC_AS_FS_BASE_URL
    fc_user_info = python_request.get(
        f"{fc_base}/userinfo?schema=openid",
        headers={"Authorization": f"Bearer {connection.access_token}"},
    )
    user_info = fc_user_info.json()

    if user_info.get("birthplace") == "":
        user_info["birthplace"] = None

    usager_sub = generate_sha256_hash(
        f"{user_info['sub']}{settings.FC_AS_FI_HASH_SALT}".encode()
    )

    try:
        usager = Usager.objects.get(sub=usager_sub)

        if usager.email != user_info.get("email"):
            usager.email = user_info.get("email")
            usager.save()

            Journal.log_update_email_usager(aidant=connection.aidant, usager=usager)

        return usager, None

    except Usager.DoesNotExist:
        try:
            usager = Usager.objects.create(
                given_name=user_info.get("given_name"),
                family_name=user_info.get("family_name"),
                birthdate=user_info.get("birthdate"),
                gender=user_info.get("gender"),
                birthplace=user_info.get("birthplace"),
                birthcountry=user_info.get("birthcountry"),
                sub=usager_sub,
                email=user_info.get("email"),
            )
            return usager, None

        except IntegrityError as e:
            log.error("Error happened in Recap")
            log.error(e)
            return None, f"The FranceConnect ID is not complete: {e}"
