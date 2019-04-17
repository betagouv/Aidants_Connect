import os
import structlog
from secrets import token_urlsafe
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect
from aidant_connect_web.models import Connection

current_host = os.getenv("HOST")
fc_callback_url = os.getenv("FC_CALLBACK_URL")
log = structlog.get_logger()


def authorize(request):
    if request.method == "GET":
        state = request.GET.get("state", False)
        if state is False:
            return HttpResponseForbidden()

        return render(request, "aidant_connect_web/authorize.html", {"state": state})

    else:
        user_info = request.POST.get("user_info")
        state = request.POST.get("state")
        if user_info == "good":
            code = token_urlsafe(64)
            this_connexion = Connection(state=state, code=code)
            this_connexion.save()

            return redirect(f"{fc_callback_url}?code={code}&state={state}")
        else:
            return HttpResponseForbidden()


def token(request):

    return HttpResponse("OK")
