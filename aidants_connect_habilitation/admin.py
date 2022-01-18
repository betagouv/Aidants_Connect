from django.contrib.admin import ModelAdmin, TabularInline, StackedInline

from django.conf import settings

from aidants_connect.admin import admin_site, VisibleToAdminMetier
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    OrganisationRequest,
    RequestMessage,
)


class IssuerAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "last_name",
        "first_name",
        "phone",
        "id",
    )


class AidantRequestInline(VisibleToAdminMetier, TabularInline):
    model = AidantRequest
    show_change_link = True


class MessageInline(VisibleToAdminMetier, StackedInline):
    model = RequestMessage
    extra = 1


class OrganisationRequestAdmin(VisibleToAdminMetier, ModelAdmin):
    list_filter = ("status",)
    list_display = ("name", "issuer", "status")
    raw_id_fields = ("issuer",)
    readonly_fields = ("public_service_delegation_attestation",)
    inlines = (
        AidantRequestInline,
        MessageInline,
    )


if settings.AC_HABILITATION_FORM_ENABLED:
    admin_site.register(Issuer, IssuerAdmin)
    admin_site.register(OrganisationRequest, OrganisationRequestAdmin)
