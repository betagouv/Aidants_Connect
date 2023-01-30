from django.conf import settings
from django.urls import path

from aidants_connect_pico_cms.views import (
    FaqCategoryView,
    FaqDefaultView,
    TestimonyView,
)

urlpatterns = [
    path("temoignages/<slug:slug>/", TestimonyView.as_view(), name="temoignage-detail"),
]

if settings.FF_USE_PICO_CMS_FOR_FAQ:
    urlpatterns.append(
        path("faq/", FaqDefaultView.as_view(), name="faq_generale"),
    )
    urlpatterns.append(
        path("faq/<slug:slug>/", FaqCategoryView.as_view(), name="faq-category-detail"),
    )
