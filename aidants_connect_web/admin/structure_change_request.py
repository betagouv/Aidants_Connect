"""Admin for StructureChangeRequest (demandes de changement de structure)."""

from django.contrib import messages
from django.contrib.admin import ModelAdmin
from django.db.models import QuerySet

from aidants_connect.admin import VisibleToAdminMetier


class StructureChangeRequestAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "aidant",
        "organisation",
        "previous_organisation",
        "new_email",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("email", "new_email", "organisation__name", "aidant__email")
    raw_id_fields = ("organisation", "previous_organisation", "aidant")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ("mark_validated",)

    fieldsets = (
        (
            "Demande",
            {
                "fields": (
                    "aidant",
                    "email",
                    "organisation",
                    "previous_organisation",
                    "new_email",
                    "status",
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def mark_validated(self, request, queryset: QuerySet):
        count = sum(1 for req in queryset if req.validate_structure_change())
        self.message_user(
            request,
            f"{count} demande(s) de changement de structure ont été validées.",
            messages.SUCCESS,
        )

    mark_validated.short_description = (
        "Valider et associer les aidants à l'organisation"
    )
