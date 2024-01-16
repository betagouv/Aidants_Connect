from django.conf import settings

from aidants_connect_web.models import Aidant


def settings_variables(request):
    return {
        "user_is_authenticated": request.user.is_authenticated,
        "user_is_responsable_structure": (
            isinstance(request.user, Aidant) and request.user.is_responsable_structure
        ),
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
        "SITE_DESCRIPTION": settings.SITE_DESCRIPTION,
        "MATOMO_INSTANCE_URL": settings.MATOMO_INSTANCE_URL,
        "MATOMO_INSTANCE_SITE_ID": settings.MATOMO_INSTANCE_SITE_ID,
        "GOUV_ADDRESS_SEARCH_API_DISABLED": settings.GOUV_ADDRESS_SEARCH_API_DISABLED,
        "GOUV_ADDRESS_SEARCH_API_BASE_URL": settings.GOUV_ADDRESS_SEARCH_API_BASE_URL,
        "AUTOCOMPLETE_SCRIPT_SRC": settings.AUTOCOMPLETE_SCRIPT_SRC,
        "SARBACANE_SCRIPT_URL": settings.SARBACANE_SCRIPT_URL,
        "SARBACANE_CONNECT_URL": settings.SARBACANE_CONNECT_URL,
        "COOKIE_BANNER_JS_URL": settings.COOKIE_BANNER_JS_URL,
        "COOKIE_BANNER_CSS_URL": settings.COOKIE_BANNER_CSS_URL,
        "COOKIE_BANNER_LANG_URL": settings.COOKIE_BANNER_LANG_URL,
        "COOKIE_BANNER_SERVICES_URL": settings.COOKIE_BANNER_SERVICES_URL,
    }
