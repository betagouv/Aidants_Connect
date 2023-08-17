import logging

from nested_admin import NestedModelAdmin, NestedTabularInline

from aidants_connect.admin import VisibleToTechAdmin
from aidants_connect_web.models import Autorisation, Mandat

from .utils import SpecificDeleteActionsMixin

logger = logging.getLogger()


class UsagerAutorisationInline(VisibleToTechAdmin, NestedTabularInline):
    model = Autorisation
    fields = ("demarche", "revocation_date")
    readonly_fields = fields
    extra = 0
    max_num = 0


class UsagerMandatInline(VisibleToTechAdmin, NestedTabularInline):
    model = Mandat
    fields = ("organisation", "creation_date", "expiration_date")
    readonly_fields = fields
    extra = 0
    max_num = 0
    inlines = (UsagerAutorisationInline,)


class UsagerAdmin(SpecificDeleteActionsMixin, VisibleToTechAdmin, NestedModelAdmin):
    list_display = ("__str__", "email", "creation_date")
    search_fields = ("given_name", "family_name", "email")

    fieldsets = (
        ("Informations", {"fields": ("given_name", "family_name", "email", "phone")}),
    )

    inlines = (UsagerMandatInline,)

    actions = ("specific_delete_action",)

    def specific_delete_action(self, request, queryset):
        self._specific_delete_action(request, queryset)

    specific_delete_action.short_description = "Supprimer les usagers sélectionnés"
