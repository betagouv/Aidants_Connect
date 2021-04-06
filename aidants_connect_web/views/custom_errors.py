from django.shortcuts import render

from sentry_sdk import capture_message


def custom_404(request, exception):
    """Observe 404 errors to log them in Sentry"""
    capture_message(f"Page not found: {request.get_full_path()}", level="error")
    return render(request, "404.html", status=404)
