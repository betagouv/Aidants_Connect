from django.urls import path

from aidants_connect_pico_cms.views import (
    AidantFaqCategoryView,
    AidantFaqDefaultView,
    FaqCategoryView,
    FaqDefaultView,
    MarkdownRenderView,
    PublicFaqCategoryView,
    PublicFaqDefaultView,
    ReferentFaqCategoryView,
    ReferentFaqDefaultView,
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
    path("faq_public/", PublicFaqDefaultView.as_view(), name="faq_public_generale"),
    path(
        "faq_public/<slug:slug>/",
        PublicFaqCategoryView.as_view(),
        name="faq_public_category_detail",
    ),
    path("faq_aidant/", AidantFaqDefaultView.as_view(), name="faq_aidant_generale"),
    path(
        "faq_aidant/<slug:slug>/",
        AidantFaqCategoryView.as_view(),
        name="faq_aidant_category_detail",
    ),
    path(
        "faq_referent/", ReferentFaqDefaultView.as_view(), name="faq_referent_generale"
    ),
    path(
        "faq_referent/<slug:slug>/",
        ReferentFaqCategoryView.as_view(),
        name="faq_referent_category_detail",
    ),
]
