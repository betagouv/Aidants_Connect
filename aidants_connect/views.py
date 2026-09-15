from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.views.static import serve as static_serve


def favicon(request):
    file = finders.find("images/favicons/favicon.ico")
    return static_serve(request, file, document_root="/")


def robots_txt(request):
    # Always allow crawling so search engines can see X-Robots-Tag / meta noindex
    # on non-production environments (required for de-indexing already indexed pages).
    # Indexing itself is controlled by ALLOW_SEARCH_ENGINE_INDEXING.
    if settings.ALLOW_SEARCH_ENGINE_INDEXING:
        content = "User-agent: *\nAllow: /\n"
    else:
        content = (
            "# Non-prod: indexing blocked via X-Robots-Tag / meta robots noindex\n"
            "User-agent: *\n"
            "Allow: /\n"
        )
    return HttpResponse(content, content_type="text/plain")
