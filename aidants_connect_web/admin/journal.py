import logging

from django.contrib.admin import ModelAdmin

from aidants_connect.admin import VisibleToTechAdmin

logger = logging.getLogger()


class JournalAdmin(VisibleToTechAdmin, ModelAdmin):
    list_display = (
        "creation_date",
        "action",
        "aidant",
        "usager",
        "additional_information",
        "id",
    )
    list_filter = ("action",)

    search_fields = (
        "action",
        "aidant__first_name",
        "aidant__last_name",
        "aidant__email",
        "usager__family_name",
        "usager__given_name",
        "usager__email",
        "additional_information",
    )
    ordering = ("-creation_date",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
