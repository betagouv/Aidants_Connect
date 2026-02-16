from django.contrib.admin import ModelAdmin

from aidants_connect.admin import VisibleToAdminMetier


class EmailStatisticsAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = ("code_email", "nb_emails_sent", "last_sent_at")


class AidantEmailStatsAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = ("aidant", "email_type", "sending_date")

    def get_sending_date_display(self, obj):
        return obj.get_sending_date_display()
