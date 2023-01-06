from django.urls import path

from aidants_connect_pico_cms.views import FaqCategoryView, TestimonyView

urlpatterns = [
    path("temoignages/<slug:slug>/", TestimonyView.as_view(), name="temoignage-detail"),
    path("faq/<slug:slug>/", FaqCategoryView.as_view(), name="faq-category-detail"),
]
