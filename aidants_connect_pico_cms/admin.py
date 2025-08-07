from django.contrib import admin
from django.contrib.admin import ModelAdmin, register
from django.forms import models
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

from aidants_connect.admin import VisibleToAdminMetier, admin_site
from aidants_connect_common.widgets import SearchableRadioSelect
from aidants_connect_pico_cms.models import (
    FaqCategory,
    FaqQuestion,
    FaqSubCategory,
    MandateTranslation,
    Testimony,
)
from aidants_connect_pico_cms.widgets import TranslationMarkdownTextarea


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

    def __init__(self, model, _admin_site):
        super().__init__(model, _admin_site)
        self.actions = (*(self.actions or []), "publish", "unpublish")

    @admin.action(description="Publie les items sélectionnés")
    def publish(self, request, queryset):
        queryset.update(published=True)

    @admin.action(description="Déplublie les items sélectionnés")
    def unpublish(self, request, queryset):
        queryset.update(published=False)


@register(Testimony, site=admin_site)
class TestimonyAdmin(CmsAdmin):
    fieldsets = (
        ("Contenu", {"fields": ("name", "job", "quote", "body")}),
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
    readonly_fields = (*CmsAdmin.readonly_fields, "slug")


@register(FaqSubCategory, site=admin_site)
class FaqSectionAdmin(CmsAdmin):
    list_display = (
        "__str__",
        "sort_order",
        "slug",
        "published",
        "created_at",
    )
    list_filter = ("published",)
    readonly_fields = (*CmsAdmin.readonly_fields, "slug")
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

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields["body"].required = False
        return form


@register(FaqCategory, site=admin_site)
class FaqCategoryAdmin(FaqSectionAdmin):
    list_display = (*FaqSectionAdmin.list_display, "theme", "see_draft")
    list_filter = ("published", "theme")
    fieldsets = (
        ("Contenu", {"fields": ("name", "body")}),
        (
            "Publication",
            {
                "fields": (
                    "published",
                    "theme",
                    "sort_order",
                    "slug",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def see_draft(self, obj):
        return mark_safe(
            f'<a href="{obj.get_absolute_url()}?see_draft" target="_blank" rel="noreferrer noopener">Voir le brouillon</a>'  # noqa
        )

    see_draft.short_description = "Voir le brouillon"


@register(FaqQuestion, site=admin_site)
class FaqQuestionAdmin(CmsAdmin):
    list_filter = ("published", "category", "category__theme")
    list_display = (
        "__str__",
        "slug",
        "category",
        "subcategory",
        "sort_order",
        "published",
        "created_at",
    )
    fieldsets = (
        ("Contenu", {"fields": ("question", "body", "category", "subcategory")}),
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
    readonly_fields = (*CmsAdmin.readonly_fields, "slug")

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields["subcategory"].required = False
        return form


class MandateTranslationAdminForm(models.ModelForm):
    class Meta:
        model = MandateTranslation
        fields = ("lang", "body")
        widgets = {
            "lang": SearchableRadioSelect(
                attrs={"data-markdown-editor-target": "langInput"}
            ),
            "body": TranslationMarkdownTextarea(
                attrs={
                    "data-markdown-editor-render-endpoint-value": reverse_lazy(
                        "mandate_translation"
                    ),
                }
            ),
        }


@register(MandateTranslation, site=admin_site)
class MandateTranslationAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = ("__str__",)
    form = MandateTranslationAdminForm
