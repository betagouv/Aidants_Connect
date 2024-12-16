from django.urls import path

from aidants_connect_pico_cms.views import (
    FaqCategoryView,
    FaqDefaultView,
    MarkdownRenderView,
    TestimoniesView,
    TestimonyView,
)

urlpatterns = [
    path("temoignages/", TestimoniesView.as_view(), name="temoignages"),
    path(
        "temoignages/<slug:slug>/", TestimonyView.as_view(), name="temoignages_detail"
    ),
    path("faq/", FaqDefaultView.as_view(), name="faq_generale"),
    path("faq/<slug:slug>/", FaqCategoryView.as_view(), name="faq_category_detail"),
    path("markdown/render/", MarkdownRenderView.as_view(), name="markdown_render"),
]
