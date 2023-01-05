from django.contrib.admin import ModelAdmin

from aidants_connect.admin import admin_site
from aidants_connect_pico_cms.models import Testimony


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


admin_site.register(Testimony, CmsAdmin)
