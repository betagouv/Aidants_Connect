from django.contrib.admin import ModelAdmin, register
from django.forms import models

from aidants_connect.admin import admin_site
from aidants_connect_common.widgets import SearchableRadioSelect
from aidants_connect_pico_cms.models import (
    FaqCategory,
    FaqQuestion,
    MandateTranslation,
    Testimony,
)


@register(Testimony, site=admin_site)
class CmsAdmin(ModelAdmin):
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
    raw_id_fields = ("updated_by",)


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


class MandateTranslationAdminForm(models.ModelForm):
    class Meta:
        model = MandateTranslation
        fields = "__all__"
        widgets = {"lang": SearchableRadioSelect}


@register(MandateTranslation, site=admin_site)
class MandateTranslationAdmin(ModelAdmin):
    list_display = ("__str__",)
    form = MandateTranslationAdminForm


admin_site.register(FaqCategory, CmsAdmin)
admin_site.register(FaqQuestion, FaqQuestionAdmin)
