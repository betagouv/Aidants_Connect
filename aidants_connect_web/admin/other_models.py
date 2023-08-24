import logging

from django.contrib.admin import ModelAdmin, register

from aidants_connect.admin import admin_site
from aidants_connect_web.models import Notification

logger = logging.getLogger()


class ConnectionAdmin(ModelAdmin):
    list_display = ("id", "usager", "aidant", "complete")
    raw_id_fields = ("usager", "aidant", "organisation")
    readonly_fields = ("autorisation",)
    search_fields = (
        "id",
        "aidant__first_name",
        "aidant__last_name",
        "aidant__email",
        "usager__family_name",
        "usager__given_name",
        "usager__email",
        "consent_request_id",
        "organisation__name",
    )


@register(Notification, site=admin_site)
class NotificationAdmin(ModelAdmin):
    date_hierarchy = "date"
    raw_id_fields = ("aidant",)
    list_display = ("type", "aidant", "date", "auto_ack_date", "was_ack")
