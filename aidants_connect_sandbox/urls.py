from django.conf import settings
from django.urls import path

from .views import AutomaticCreationViewAPI

path_url = f"sandbox/{settings.SANDBOX_URL_PADDING}/automatic_creation/"
urlpatterns = [
    path(
        path_url, AutomaticCreationViewAPI.as_view(), name="sandbox_automatic_creation"
    )
]
