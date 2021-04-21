from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.utils import timezone


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
    requires the user to be :term:`responsable structure`.
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
