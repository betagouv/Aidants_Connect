import logging
import jwt
import time
import re
from datetime import date
from secrets import token_urlsafe

from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.messages import get_messages

from aidants_connect_web.models import (
    Connection,
    Mandat,
    Usager,
    CONNECTION_EXPIRATION_TIME,
)
from aidants_connect_web.forms import UsagerForm, MandatForm, FCForm


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def humanize_demarche_names(list_of_machine_names):
    human_names = []
    for p in list_of_machine_names:
        for category in settings.DEMARCHES:
            for element in category[1]:
                if element[0] == p:
                    human_names.append(element[1])
    return human_names


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request, "aidants_connect_web/home_page.html", {"random_string": random_string}
    )


@login_required
def logout_page(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def dashboard(request):
    messages = get_messages(request)
    user = request.user
    mandats = Mandat.objects.all().filter(aidant=request.user).order_by("creation_date")

    for mandat in mandats:
        mandat.perimeter_names = humanize_demarche_names(mandat.perimeter)

    return render(
        request,
        "aidants_connect_web/dashboard.html",
        {"user": user, "mandats": mandats, "messages": messages},
    )


@login_required
def mandat(request):

    user = request.user
    form = MandatForm()

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/mandat/mandat.html",
            {"user": user, "form": form},
        )

    else:
        form = MandatForm(request.POST)

        if form.is_valid():
            request.session["mandat"] = form.cleaned_data

            return redirect("france_connect")
        else:
            return render(
                request,
                "aidants_connect_web/mandat/mandat.html",
                {"user": user, "form": form},
            )


@login_required
def france_connect(request):

    if request.method == "GET":
        form = FCForm()

        return render(
            request, "aidants_connect_web/mandat/france_connect.html", {"form": form}
        )
    else:
        form = FCForm(request.POST)
        if form.is_valid():
            request.session["usager"] = {
                "given_name": form.cleaned_data["given_name"],
                "family_name": form.cleaned_data["family_name"],
            }
            return redirect("recap")
        else:
            return render(
                request,
                "aidants_connect_web/mandat/france_connect.html",
                {"form": form},
            )


@login_required
def recap(request):
    user = request.user
    usager = Usager(
        given_name=request.session.get("usager")["given_name"],
        family_name=request.session.get("usager")["family_name"],
        birthdate=date(1945, 10, 20),
        gender="M",
        birthplace="84016",
        birthcountry="99100",
        email="user@test.fr",
    )

    mandat = request.session.get("mandat")

    if request.method == "GET":
        demarches = humanize_demarche_names(mandat["perimeter"])

        return render(
            request,
            "aidants_connect_web/mandat/recap.html",
            {
                "user": user,
                "usager": usager,
                "demarches": demarches,
                "duration": mandat["duration"],
            },
        )

    else:
        form = request.POST

        if form.get("personal_data") and form.get("brief"):
            mandat["aidant"] = user

            usager.save()
            mandat["usager"] = usager

            new_mandat = Mandat.objects.create(**mandat)
            log.info(type(new_mandat.perimeter))

            messages.success(request, "Le mandat a été créé avec succès !")

            return redirect("dashboard")

        else:
            return render(
                request,
                "aidants_connect_web/mandat/recap.html",
                {
                    "user": user,
                    "usager": usager,
                    "demarche": demarches,
                    "duration": mandat["duration"],
                    "error": "Vous devez accepter les conditions du mandat.",
                },
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
