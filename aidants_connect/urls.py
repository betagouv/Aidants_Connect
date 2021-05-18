from django.conf import settings
from django.urls import path, include
from django.views.decorators.cache import cache_page
from django_js_reverse.views import urls_js

from aidants_connect import views
from aidants_connect_web.admin import admin_site


urlpatterns = [
    path("favicon.ico", views.favicon),
    path(settings.ADMIN_URL, admin_site.urls),
    path("admin/", include("admin_honeypot.urls", namespace="admin_honeypot")),
    path("", include("aidants_connect_web.urls")),
    path("jsreverse/", cache_page(3600)(urls_js), name="js_reverse"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
