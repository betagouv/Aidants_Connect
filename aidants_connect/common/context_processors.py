from django.conf import settings


def settings_variables(request):
    return {
        "MATOMO_INSTANCE_URL": settings.MATOMO_INSTANCE_URL,
        "MATOMO_INSTANCE_SITE_ID": settings.MATOMO_INSTANCE_SITE_ID,
    }
