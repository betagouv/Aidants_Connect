from django.urls import path

from aidants_connect_pico_cms.views import (
    FaqCategoryView,
    FaqDefaultView,
    TestimonyView,
)

urlpatterns = [
    path("temoignages/<slug:slug>/", TestimonyView.as_view(), name="temoignage-detail"),
    path("faq/", FaqDefaultView.as_view(), name="faq_generale"),
    path("faq/<slug:slug>/", FaqCategoryView.as_view(), name="faq-category-detail"),
]
