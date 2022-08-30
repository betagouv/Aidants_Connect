from django.conf import settings


def settings_variables(request):
    return {
        "MATOMO_INSTANCE_URL": settings.MATOMO_INSTANCE_URL,
        "MATOMO_INSTANCE_SITE_ID": settings.MATOMO_INSTANCE_SITE_ID,
        "GOUV_ADDRESS_SEARCH_API_DISABLED": settings.GOUV_ADDRESS_SEARCH_API_DISABLED,
        "GOUV_ADDRESS_SEARCH_API_BASE_URL": settings.GOUV_ADDRESS_SEARCH_API_BASE_URL,
        "AUTOCOMPLETE_SCRIPT_SRC": settings.AUTOCOMPLETE_SCRIPT_SRC,
    }
