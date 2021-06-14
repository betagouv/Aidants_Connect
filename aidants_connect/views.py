from django.contrib.staticfiles import finders
from django.views.static import serve as static_serve


def favicon(request):
    file = finders.find("images/favicons/favicon.ico")
    return static_serve(request, file, document_root="/")
