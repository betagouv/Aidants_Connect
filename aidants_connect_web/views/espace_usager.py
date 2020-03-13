from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from aidants_connect_web.models import Connection


def espace_usager_home(request):
    state = request.GET.get("state")
    try:
        connection = Connection.objects.get(state=state)
    except Connection.DoesNotExist:
        # return HttpResponseForbidden()
        messages.error(request, "Erreur lors de l'accès à l'Espace Usager.")
        return redirect("home_page")

    if connection.expires_on < timezone.now():
        # return HttpResponseForbidden()
        messages.error(request, "La connexion a expiré. Veuillez réessayer.")
        return redirect("home_page")

    active_mandats = connection.usager.mandats.active()
    expired_mandats = connection.usager.mandats.expired()

    return render(
        request,
        "aidants_connect_web/espace_usager/espace_usager_home.html",
        {
            "usager": connection.usager,
            "active_mandats": active_mandats,
            "expired_mandats": expired_mandats,
        },
    )
