import sys

from django.conf import settings
from django.urls import include, path

from django_js_reverse.views import urls_js as django_js_reverse_urls

from aidants_connect import views
from aidants_connect_common.tests import third_party_service_mocks
from aidants_connect_web.admin import admin_site

urlpatterns = [
    path("favicon.ico", views.favicon),
    path(settings.ADMIN_URL, admin_site.urls),
    path("jsreverse/", django_js_reverse_urls, name="js_reverse"),
    path("", include("aidants_connect_common.urls")),
    path("", include("aidants_connect_web.urls")),
    path("habilitation/", include("aidants_connect_habilitation.urls")),
    path("", include("aidants_connect_pico_cms.urls")),
    # APIs
    path(
        "api/habilitation/",
        include("aidants_connect_habilitation.api.urls"),
    ),
    path(
        "api/web/",
        include("aidants_connect_web.api.urls"),
    ),
]

if "test" in sys.argv:
    urlpatterns.append(
        path(
            "third_party_service_mocks/",
            include(third_party_service_mocks.urls),
        )
    )

if settings.DEBUG and "test" not in sys.argv:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
