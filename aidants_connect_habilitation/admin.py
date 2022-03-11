from django.conf import settings
from django.contrib.admin import ModelAdmin, StackedInline, TabularInline

from django_reverse_admin import ReverseModelAdmin

from aidants_connect.admin import (
    DepartmentFilter,
    RegionFilter,
    VisibleToAdminMetier,
    admin_site,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    OrganisationRequest,
    RequestMessage,
)


class OrganisationRequestInline(VisibleToAdminMetier, TabularInline):
    model = OrganisationRequest
    show_change_link = True
    fields = ("id", "status", "name", "type", "address", "zipcode", "city")
    readonly_fields = fields
    extra = 0
    can_delete = False


class IssuerAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "last_name",
        "first_name",
        "phone",
    )
    readonly_fields = ("issuer_id",)
    inlines = (OrganisationRequestInline,)


class AidantRequestInline(VisibleToAdminMetier, TabularInline):
    model = AidantRequest
    show_change_link = True
    extra = 0


class MessageInline(VisibleToAdminMetier, StackedInline):
    model = RequestMessage
    extra = 1


class OrganisationRequestAdmin(VisibleToAdminMetier, ReverseModelAdmin):
    list_filter = ("status", RegionFilter, DepartmentFilter)
    list_display = ("name", "issuer", "status")
    raw_id_fields = ("issuer",)
    readonly_fields = ("public_service_delegation_attestation", "draft_id")
    inlines = (
        AidantRequestInline,
        MessageInline,
    )
    inline_type = "stacked"
    inline_reverse = (
        "manager",
        "data_privacy_officer",
    )


if settings.AC_HABILITATION_FORM_ENABLED:
    admin_site.register(Issuer, IssuerAdmin)
    admin_site.register(OrganisationRequest, OrganisationRequestAdmin)
