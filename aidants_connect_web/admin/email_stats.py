from django.contrib.admin import ModelAdmin

from aidants_connect.admin import VisibleToAdminMetier


class EmailStatisticsAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = ("code_email", "nb_emails_sent", "last_sent_at")
    list_filter = ("code_email",)


class AidantEmailStatsAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "aidant",
        "email_type",
        "sending_date",
        "code_email",
        "sending_date",
    )
    readonly_fields = ("aidant",)
    search_fields = ("aidant__email",)
    list_filter = ("code_email",)

    def get_sending_date_display(self, obj):
        return obj.get_sending_date_display()
