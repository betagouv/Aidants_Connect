from django.conf import settings
from django.urls import path, include

from aidants_connect_web.admin import admin_site

urlpatterns = [
    path(settings.ADMIN_URL, admin_site.urls),
    path("admin/", include("admin_honeypot.urls", namespace="admin_honeypot")),
    path("", include("aidants_connect_web.urls")),
]
handler404 = "aidants_connect_web.views.custom_errors.custom_404"

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
