from typing import List

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.utils.decorators import method_decorator


def activity_required(view=None, redirect_field_name="next"):
    """
    Similar to :func:`~django.contrib.auth.decorators.login_required`, but
    requires the user to be :term:`verified`. By default, this redirects users
    to :setting:`ACTIVITY_CHECK_URL`.

    """

    def test(user):
        user_last_action_ts = user.get_last_action_timestamp()
        if not user_last_action_ts:
            return False
        time_since_last_action = timezone.now() - user_last_action_ts
        is_alive = time_since_last_action < settings.ACTIVITY_CHECK_DURATION
        return is_alive

    decorator = user_passes_test(
        test,
        login_url=settings.ACTIVITY_CHECK_URL,
        redirect_field_name=redirect_field_name,
    )
    return decorator if (view is None) else decorator(view)


def user_is_aidant(view=None, redirect_field_name="next"):
    """
    Similar to :func:`~django.contrib.auth.decorators.login_required`, but
    requires the user to be :term:`allowed to create mandats`.
    By default, this redirects users to home of espace aidants.
    """

    def test(user):
        return user.can_create_mandats

    decorator = user_passes_test(
        test,
        login_url="espace_aidant_home",
        redirect_field_name=redirect_field_name,
    )
    return decorator if (view is None) else decorator(view)


def user_is_responsable_structure(view=None, redirect_field_name="next"):
    """
    Similar to :func:`~django.contrib.auth.decorators.login_required`, but
    requires the user to be :term:`référent structure`.
    By default, this redirects users to home of espace aidants.
    """

    def test(user):
        return user.is_responsable_structure()

    decorator = user_passes_test(
        test,
        login_url="espace_aidant_home",
        redirect_field_name=redirect_field_name,
    )
    return decorator if (view is None) else decorator(view)


def aidant_logged_required(
    view=None, *, method_name="", more_decorators: List | None = None
):
    """
    Combines @login_required, @user_is_aidant and for CBVs.

    Can be applied to either the class itself or any method of the class.
    If applied on the class, will be applied on ``dispatch`` method by default
    but can be changed by using ``method_name`` argument.

    ``additionnal_decorators`` allows to decorate the view with additionnal decorators,
    like csrf_exempt.
    """

    def decorator(decorated):
        kwargs = {}
        if isinstance(decorated, type) and not method_name:
            kwargs["name"] = method_name or "dispatch"

        more = more_decorators or []

        fun = method_decorator([login_required, user_is_aidant, *more], **kwargs)

        return fun(decorated)

    return decorator(view) if view else decorator


def aidant_logged_with_activity_required(
    view=None, *, method_name="", more_decorators: List | None = None
):
    """
    Combines @login_required, @user_is_aidant and @activity_required for CBVs.

    Can be applied to either the class itself or any method of the class.
    If applied on the class, will be applied on ``dispatch`` method by default
    but can be changed by using ``method_name`` argument.

    ``additionnal_decorators`` allows to decorate the view with additionnal decorators,
    like csrf_exempt.
    """

    more_decorators = [activity_required] + (more_decorators or [])
    return aidant_logged_required(
        view=view, method_name=method_name, more_decorators=more_decorators
    )
