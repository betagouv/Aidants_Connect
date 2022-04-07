from django.conf import settings
from django.contrib import messages
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
from aidants_connect_web.models import Organisation


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
    list_display = ("name", "issuer", "status", "data_pass_id")
    search_fields = ("data_pass_id", "name")
    raw_id_fields = ("issuer", "organisation")
    readonly_fields = ("public_service_delegation_attestation", "uuid", "organisation")
    inlines = (
        AidantRequestInline,
        MessageInline,
    )
    inline_type = "stacked"
    inline_reverse = ("manager",)

    actions = ("accept_request",)

    def accept_request(self, request, queryset):
        orgs_created = 0
        for organisation_request in queryset:
            try:
                if organisation_request.accept_request_and_create_organisation():
                    orgs_created += 1
            except Organisation.AlreadyExists as e:
                self.message_user(request, e, level=messages.ERROR)
        if orgs_created > 1:
            self.message_user(
                request,
                f"{orgs_created} organisations ont été créées.",
                level=messages.SUCCESS,
            )
        elif orgs_created == 1:
            self.message_user(
                request, "Une organisation a été créée.", level=messages.SUCCESS
            )

    accept_request.short_description = (
        "Accepter les demandes sélectionnées "
        "(créer les organisations et les aidants à former)"
    )


if settings.AC_HABILITATION_FORM_ENABLED:
    admin_site.register(Issuer, IssuerAdmin)
    admin_site.register(OrganisationRequest, OrganisationRequestAdmin)
