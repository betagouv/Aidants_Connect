from django.contrib.admin import ModelAdmin, register
from django.forms import models

from aidants_connect.admin import VisibleToAdminMetier, admin_site
from aidants_connect_common.widgets import SearchableRadioSelect
from aidants_connect_pico_cms.models import (
    FaqCategory,
    FaqQuestion,
    MandateTranslation,
    Testimony,
)


class CmsAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "__str__",
        "slug",
        "sort_order",
        "published",
        "created_at",
    )
    list_filter = ("published",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@register(Testimony, site=admin_site)
class TestimonyAdmin(CmsAdmin):
    fieldsets = (
        ("Contenu", {"fields": ("name", "job", "body")}),
        (
            "Publication",
            {
                "fields": (
                    "published",
                    "sort_order",
                    "slug",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@register(FaqCategory, site=admin_site)
class FaqCategoryAdmin(CmsAdmin):
    fieldsets = (
        ("Contenu", {"fields": ("name", "body")}),
        (
            "Publication",
            {
                "fields": (
                    "published",
                    "sort_order",
                    "slug",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@register(FaqQuestion, site=admin_site)
class FaqQuestionAdmin(CmsAdmin):
    list_filter = ("published", "category")
    list_display = (
        "__str__",
        "slug",
        "category",
        "sort_order",
        "published",
        "created_at",
    )
    fieldsets = (
        ("Contenu", {"fields": ("question", "body", "category")}),
        (
            "Publication",
            {
                "fields": (
                    "published",
                    "sort_order",
                    "slug",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


class MandateTranslationAdminForm(models.ModelForm):
    class Meta:
        model = MandateTranslation
        fields = "__all__"
        widgets = {"lang": SearchableRadioSelect}


@register(MandateTranslation, site=admin_site)
class MandateTranslationAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = ("__str__",)
    form = MandateTranslationAdminForm
