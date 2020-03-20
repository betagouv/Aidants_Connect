import logging
from secrets import token_urlsafe
import jwt
from jwt.api_jwt import ExpiredSignatureError
import requests as python_request

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from aidants_connect_web.models import Connection, Usager, Journal
from aidants_connect_web.utilities import generate_sha256_hash


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def fc_authorize(request, source):
    if source == "espace_usager":
        connection = Connection.objects.create()
        request.session["connection"] = connection.pk

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
    parameters = {
        "state": request.GET.get("state"),
        "code": request.GET.get("code"),
    }

    try:
        connection = Connection.objects.get(state=parameters["state"])
    except Connection.DoesNotExist:
        log.info("FC as FS - This state does not seem to exist")
        log.info(parameters["state"])
        return HttpResponseForbidden()

    if connection.is_expired:
        log.info("408: FC connection has expired.")
        return render(request, "408.html", status=408)

    if not parameters["code"]:
        log.info("403: No code has been provided.")
        return HttpResponseForbidden()

    token = get_token(code=parameters["code"])

    connection.access_token = token.get("access_token")
    connection.save()

    fc_id_token = token.get("id_token")
    request.session["id_token_hint"] = fc_id_token

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

    usager_sub = generate_sha256_hash(
        f"{decoded_token['sub']}{settings.FC_AS_FI_HASH_SALT}".encode()
    )

    user_info = get_user_info(access_token=connection.access_token)

    try:
        usager = Usager.objects.get(sub=usager_sub)
    except Usager.DoesNotExist:
        # new_mandat workflow: create usager
        if connection.aidant:
            if user_info.get("birthplace") == "":
                user_info["birthplace"] = None

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
            except IntegrityError as e:
                log.error("Error happened in Recap")
                log.error(e)
                messages.error(request, f"The FranceConnect ID is not complete: {e}")
                return redirect("home_page")

        # espace_usager workflow: redirect to home page
        else:
            messages.error(
                request,
                "La connexion à Aidants Connect a échoué."
                "Vous n'êtes pas un usager ayant déjà été accompagné "
                "sur Aidants Connect.",
            )
            return redirect("home_page")

    # update usager email if it has changed
    if usager.email != user_info.get("email"):
        usager.email = user_info.get("email")
        usager.save()

        Journal.objects.update_email_usager(aidant=connection.aidant, usager=usager)

    connection.usager = usager
    connection.save()

    Journal.objects.franceconnection_usager(
        aidant=connection.aidant, usager=connection.usager,
    )

    # new_mandat workflow
    if connection.aidant:
        logout_url = fc_user_logout_url(
            id_token_hint=request.session["id_token_hint"],
            state=connection.state,
            callback_uri_logout=f"{settings.FC_AS_FS_CALLBACK_URL}/logout-callback",
        )
        return redirect(logout_url)
    # espace_usager workflow
    else:
        return redirect("espace_usager_mandats")


def get_token(code: str) -> dict:
    token_url = f"{settings.FC_AS_FS_BASE_URL}/token"
    payload = {
        "grant_type": "authorization_code",
        "redirect_uri": f"{settings.FC_AS_FS_CALLBACK_URL}/callback",
        "client_id": settings.FC_AS_FS_ID,
        "client_secret": settings.FC_AS_FS_SECRET,
        "code": code,
    }
    headers = {"Accept": "application/json"}

    request_token = python_request.post(token_url, data=payload, headers=headers)
    fc_token_json = request_token.json()
    return fc_token_json


def get_user_info(access_token: str) -> dict:
    user_info_url = f"{settings.FC_AS_FS_BASE_URL}/userinfo?schema=openid"
    headers = {"Authorization": f"Bearer {access_token}"}

    request_user_info = python_request.get(user_info_url, headers=headers)
    fc_user_info_json = request_user_info.json()
    return fc_user_info_json


def fc_user_logout_url(id_token_hint: str, state: str, callback_uri_logout: str) -> str:
    logout_base = f"{settings.FC_AS_FS_BASE_URL}/logout"
    logout_id_token = f"id_token_hint={id_token_hint}"
    logout_state = f"state={state}"
    logout_redirect = f"post_logout_redirect_uri={callback_uri_logout}"
    logout_url = f"{logout_base}?{logout_id_token}&{logout_state}&{logout_redirect}"
    return logout_url
