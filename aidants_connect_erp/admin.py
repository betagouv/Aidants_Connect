import logging

from django.contrib.admin import ModelAdmin
from django.forms import models

from import_export.admin import ImportMixin

from aidants_connect.admin import VisibleToAdminMetier, admin_site

from .models import CardSending, get_bizdev_users

logger = logging.getLogger()


class CardSendingAdminForm(models.ModelForm):
    class Meta:
        model = CardSending
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(CardSendingAdminForm, self).__init__(*args, **kwargs)
        self.fields["referent"].queryset = get_bizdev_users()


class CardSendingAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
    form = CardSendingAdminForm
    list_display = (
        "created_at",
        "sending_date",
        "get_organisation_data_pass_id",
        "organisation",
        "referent",
        "get_referent_email",
        "get_referent_phone",
        "get_organisation_address",
        "get_organisation_zipcode",
        "get_organisation_city",
        "get_organisation_region_name",
        "code_referent",
        "quantity",
        "estimated_quantity",
        "bizdev",
        "status",
        "raison_envoi",
        "get_sending_year",
        "command_number",
    )
    raw_id_fields = ("organisation", "referent")
    list_filter = ("status",)

    search_fields = (
        "organisation__name",
        "organisation__city",
        "referent__first_name",
        "referent__last_name",
        "referent__email",
    )
    raw_id_fields = ("aidants",)


admin_site.register(CardSending, CardSendingAdmin)
