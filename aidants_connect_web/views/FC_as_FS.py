import logging
from secrets import token_urlsafe
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages as django_messages
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse

import jwt
import requests as python_request
from jwt.api_jwt import ExpiredSignatureError

from aidants_connect_web.models import Connection, Journal, Usager
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
        "openid",
        "email",
        "gender",
        "birthdate",
        "birthplace",
        "given_name",
        "family_name",
        "birthcountry",
    ]
    if settings.GET_PREFERRED_USERNAME_FROM_FC:
        fc_scopes.append("preferred_username")

    parameters = (
        f"response_type=code"
        f"&client_id={fc_id}"
        f"&redirect_uri={fc_callback_uri}"
        f"&scope={'%20'.join(fc_scopes)}"
        f"&state={connection.state}"
        f"&nonce={connection.nonce}"
        f"&acr_values=eidas1"
    )

    authorize_url = f"{fc_base}/authorize?{parameters}"

    return redirect(authorize_url)


def fc_callback(request):
    def fc_error(log_msg, connection_id=None):
        log.error(log_msg)
        django_messages.error(
            request,
            "Nous avons rencontré une erreur en tentant d'interagir avec "
            "France Connect. C'est probabablement temporaire. Pouvez-vous réessayer "
            "votre requête ?",
        )

        query_params = (
            f"?{urlencode({'connection_id': connection_id})}" if connection_id else ""
        )

        return redirect(f"{reverse('new_mandat')}{query_params}")

    fc_base = settings.FC_AS_FS_BASE_URL
    fc_callback_uri = f"{settings.FC_AS_FS_CALLBACK_URL}/callback"
    fc_callback_uri_logout = f"{settings.FC_AS_FS_CALLBACK_URL}/logout-callback"
    fc_id = settings.FC_AS_FS_ID
    fc_secret = settings.FC_AS_FS_SECRET
    state = request.GET.get("state")

    try:
        connection = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        return fc_error(f"FC as FS - This state does not seem to exist: {state}")

    if request.GET.get("error"):
        return fc_error(
            f"FranceConnect returned an error: "
            f"{request.GET.get('error_description')}",
            connection.pk,
        )

    if connection.is_expired:
        return fc_error("408: FC connection has expired.", connection.pk)

    code = request.GET.get("code")
    if not code:
        return fc_error("FC AS FS: no code has been provided", connection.pk)

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

    try:
        content = request_for_token.json()
    except ValueError:  # not a valid JSON
        return fc_error(
            f"Request to {token_url} failed. Status code: "
            f"{request_for_token.status_code}, body: {request_for_token.text}",
            connection.pk,
        )

    connection.access_token = content.get("access_token")
    if connection.access_token is None:
        return fc_error(
            f"No access_token return when requesting {token_url}. JSON response: "
            f"{repr(content)}",
            connection.pk,
        )

    connection.save()
    fc_id_token = content.get("id_token")

    try:
        decoded_token = jwt.decode(
            fc_id_token,
            settings.FC_AS_FS_SECRET,
            audience=settings.FC_AS_FS_ID,
            algorithms=["HS256"],
        )
    except ExpiredSignatureError:
        return fc_error("403: token signature has expired.", connection.pk)

    if connection.nonce != decoded_token.get("nonce"):
        return fc_error(
            "FC as FS: The nonce is different than the one expected", connection.pk
        )

    if connection.is_expired:
        log.info("408: FC connection has expired.", connection.pk)
        return render(request, "408.html", status=408)

    usager, error = get_user_info(connection)
    if error:
        return fc_error(error, connection.pk)

    connection.usager = usager
    connection.save()

    Journal.log_franceconnection_usager(
        aidant=connection.aidant,
        usager=connection.usager,
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

    user_phone = connection.user_phone if len(connection.user_phone) > 0 else None

    if user_info.get("birthplace") == "":
        user_info["birthplace"] = None

    user_sub = user_info.get("sub")
    if not user_sub:
        return None, "Unable to find sub in FC user info"

    usager_sub = generate_sha256_hash(
        f"{user_sub}{settings.FC_AS_FI_HASH_SALT}".encode()
    )

    try:
        usager = Usager.objects.get(sub=usager_sub)

        if usager.email != user_info.get("email"):
            usager.email = user_info.get("email")
            usager.save()
            Journal.log_update_email_usager(aidant=connection.aidant, usager=usager)

        if user_phone is not None and usager.phone != user_phone:
            usager.phone = user_phone
            Journal.log_update_phone_usager(aidant=connection.aidant, usager=usager)
            usager.save()

        if not usager.preferred_username and user_info.get("preferred_username"):
            usager.preferred_username = user_info.get("preferred_username")
            usager.save()

        return usager, None

    except Usager.DoesNotExist:
        kwargs = {
            "given_name": user_info.get("given_name"),
            "family_name": user_info.get("family_name"),
            "birthdate": user_info.get("birthdate"),
            "gender": user_info.get("gender"),
            "birthplace": user_info.get("birthplace"),
            "birthcountry": user_info.get("birthcountry"),
            "preferred_username": user_info.get("preferred_username"),
            "sub": usager_sub,
            "email": user_info.get("email"),
        }

        if user_phone is not None:
            kwargs["phone"] = user_phone

        try:
            usager = Usager.objects.create(**kwargs)
            return usager, None

        except IntegrityError as e:
            log.error("Error happened in Recap")
            log.error(e)
            return None, f"The FranceConnect ID is not complete: {e}"
