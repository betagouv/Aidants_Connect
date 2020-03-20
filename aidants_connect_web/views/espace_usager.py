from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from aidants_connect_web.models import Connection
from aidants_connect_web.views.FC_as_FS import fc_user_logout_url


def espace_usager_mandats(request):
    try:
        connection = Connection.objects.get(pk=request.session["connection"])
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
        "aidants_connect_web/espace_usager/espace_usager_mandats.html",
        {
            "usager": connection.usager,
            "active_mandats": active_mandats,
            "expired_mandats": expired_mandats,
        },
    )


def espace_usager_logout(request):
    try:
        connection = Connection.objects.get(pk=request.session["connection"])
    except Connection.DoesNotExist:
        # return HttpResponseForbidden()
        messages.error(request, "Erreur lors de l'accès à l'Espace Usager.")
        return redirect("home_page")

    connection.expires_on = timezone.now()
    connection.save()

    messages.success(request, "Votre déconnexion a été effectuée avec succès.")
    logout_url = fc_user_logout_url(
        id_token_hint=request.session["id_token_hint"],
        state=connection.state,
        callback_uri_logout=f"{settings.FC_AS_FS_CALLBACK_URL}/logout",
    )
    return redirect(logout_url)
