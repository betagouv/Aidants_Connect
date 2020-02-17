from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.utils import timezone

from aidants_connect_web.models import Mandat


def activity_required(view=None, redirect_field_name="next"):
    """
    Similar to :func:`~django.contrib.auth.decorators.login_required`, but
    requires the user to be :term:`verified`. By default, this redirects users
    to :setting:`ACTIVITY_CHECK_URL`.

    """

    def test(user):
        time_since_last_action = timezone.now() - user.get_last_action_timestamp()
        is_alive = time_since_last_action < settings.ACTIVITY_CHECK_DURATION
        return is_alive

    decorator = user_passes_test(
        test,
        login_url=settings.ACTIVITY_CHECK_URL,
        redirect_field_name=redirect_field_name,
    )
    return decorator if (view is None) else decorator(view)


def check_mandat_usager(func):
    """
    Decorator that checks that the mandat_id corresponds to the usager_id
    specified in the request url
    """

    def actual_decorator(request, *args, **kwargs):
        mandat = get_object_or_404(Mandat, pk=kwargs["mandat_id"])
        if not (mandat.usager_id == kwargs["usager_id"]):
            messages.error(request, f"Erreur de permissions")
            return redirect("dashboard")
        return func(request, *args, **kwargs)

    return actual_decorator


def check_mandat_aidant(func):
    """
    Decorator that checks that the mandat_id was created by
    the current user (the logged in Aidant)
    TODO: manage futur Organisation roles
    """

    def actual_decorator(request, *args, **kwargs):
        mandat = get_object_or_404(Mandat, pk=kwargs["mandat_id"])
        if not (mandat.aidant_id == request.user.id):
            messages.error(request, f"Erreur de permissions")
            return redirect("dashboard")
        return func(request, *args, **kwargs)

    return actual_decorator


def check_mandat_is_not_expired(func):
    """
    Decorator that checks that the mandat_id is not yet expired
    """

    def actual_decorator(request, *args, **kwargs):
        mandat = get_object_or_404(Mandat, pk=kwargs["mandat_id"])
        if mandat.is_expired:
            messages.error(request, f"Le mandat est déjà expiré")
            return redirect("dashboard")
        return func(request, *args, **kwargs)

    return actual_decorator
