from uuid import uuid4
from secrets import token_urlsafe

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods, require_GET

from phonenumbers import (
    PhoneNumber,
    PhoneNumberFormat,
    format_number,
)

from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Connection, Journal, Aidant, Usager
from aidants_connect_web.sms_api import api
from aidants_connect_web.views.mandat import __remote_pending
from aidants_connect_web.constants import (
    RemotePendingResponses,
    AuthorizationDurations,
)


@login_required
@user_is_aidant
@activity_required
@require_http_methods(["GET", "POST"])
def renew_mandat(request, usager_id):
    aidant: Aidant = request.user
    usager: Usager = aidant.get_usager(usager_id)

    if not usager:
        django_messages.error(request, "Cet usager est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/new_mandat/renew_mandat.html",
            {"aidant": aidant, "form": MandatForm()},
        )

    form = MandatForm(request.POST)

    if not form.is_valid():
        return render(
            request,
            "aidants_connect_web/new_mandat/renew_mandat.html",
            {"aidant": aidant, "form": form},
        )

    data = form.cleaned_data
    is_remote = data["is_remote"]
    access_token = make_password(token_urlsafe(64), settings.FC_AS_FI_HASH_SALT)
    duree = AuthorizationDurations.duration(data["duree"])
    kwargs = {
        "aidant": request.user,
        "connection_type": "FS",
        "access_token": access_token,
        "usager": usager,
        "demarches": data["demarche"],
        "duree_keyword": data["duree"],
        "mandat_is_remote": is_remote,
    }

    if is_remote:
        user_phone: PhoneNumber = data["user_phone"]

        sms_tag = str(uuid4())

        # Try to choose another UUID if there's already one
        # associated with this number in DB.
        while Journal.find_consent_requests(user_phone, sms_tag).count() != 0:
            sms_tag = str(uuid4())

        kwargs["user_phone"] = format_number(user_phone, PhoneNumberFormat.E164)
        kwargs["consent_request_tag"] = sms_tag

        api.send_sms_for_response(
            user_phone,
            sms_tag,
            render_to_string("aidants_connect_web/sms_consent_request.txt"),
        )

        Journal.log_consent_request_sent(
            aidant=aidant,
            user_phone=user_phone,
            consent_request_tag=sms_tag,
            demarche=data["demarche"],
            duree=duree,
        )

    connection = Connection.objects.create(**kwargs)
    Journal.log_init_renew_mandat(
        aidant=aidant,
        usager=usager,
        demarches=connection.demarches,
        duree=duree,
        is_remote_mandat=connection.mandat_is_remote,
        access_token=connection.access_token,
    )

    request.session["connection"] = connection.pk
    return (
        redirect("renew_mandat_remote_pending")
        if is_remote
        else redirect("new_mandat_recap")
    )


@login_required
@user_is_aidant
@activity_required
@require_GET
def remote_pending(request):
    result = __remote_pending(request)

    if result == RemotePendingResponses.INVALID_CONNECTION:
        django_messages.error(
            request,
            "Il n'y a aucun mandat à distance actuellement en cours de création",
        )
        return redirect("home_page")
    elif result == RemotePendingResponses.NOT_DRAFT_CONNECTION:
        return redirect("new_mandat_recap")
    elif result == RemotePendingResponses.NO_CONSENT:
        return render(request, "aidants_connect_web/new_mandat/remote_pending.html")

    return redirect("new_mandat_recap")
