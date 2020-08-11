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
