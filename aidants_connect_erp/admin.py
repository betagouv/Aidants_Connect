import logging

from django.contrib.admin import ModelAdmin

from import_export.admin import ImportMixin

from aidants_connect.admin import VisibleToAdminMetier, admin_site

from .models import CardSending

logger = logging.getLogger()


class CardSendingAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "sending_date",
        "organisation",
        "quantity",
        "status",
        "command_number",
    )
    list_filter = ("status",)

    raw_id_fields = ("organisation",)


admin_site.register(CardSending, CardSendingAdmin)
