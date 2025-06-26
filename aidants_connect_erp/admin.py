import logging

from django.contrib.admin import ModelAdmin, TabularInline
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


class AidantInCardSendingInlineAdmin(TabularInline):
    model = CardSending.aidants.through
    show_change_link = True
    can_delete = False
    extra = 0

    def has_change_permission(self, request, obj):
        return False

    def first_name(self, instance):
        return instance.aidant.first_name if instance.aidant else "-"

    def last_name(self, instance):
        return instance.aidant.last_name if instance.aidant else "-"

    first_name.short_description = "Prénom"
    last_name.short_description = "Nom de Famille"

    def get_readonly_fields(self, request, obj=None):
        return (
            list(super().get_readonly_fields(request, obj))
            + ["first_name"]
            + ["last_name"]
        )

    raw_id_fields = ("aidant",)


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
    raw_id_fields = (
        "organisation",
        "referent",
        "aidants",
    )
    list_filter = ("status",)

    search_fields = (
        "organisation__name",
        "organisation__city",
        "referent__first_name",
        "referent__last_name",
        "referent__email",
    )
    inlines = (AidantInCardSendingInlineAdmin,)


admin_site.register(CardSending, CardSendingAdmin)
