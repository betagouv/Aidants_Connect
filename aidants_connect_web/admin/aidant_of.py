from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from aidants_connect.admin import VisibleToOFAdmin
from aidants_connect_web.of_forms import OFAidantChangeForm, OFAidantCreationForm


class AidantOFAdmin(VisibleToOFAdmin, DjangoUserAdmin):
    # The forms to add and change `Aidant` instances
    form = OFAidantChangeForm
    add_form = OFAidantCreationForm
    raw_id_fields = ("responsable_de", "organisation", "organisations")
    readonly_fields = (
        "created_at",
        "updated_at",
        "id_fne",
        "is_staff",
        "is_of_user",
        "is_admin_metier",
        "is_superuser",
        "organisation",
    )

    # The fields to be used in displaying the `Aidant` model.
    # These override the definitions on the base `UserAdmin`
    # that references specific fields on `auth.User`.
    list_display = (
        "__str__",
        "id",
        "email",
        "organisation",
        "is_active",
        "created_at",
    )

    list_filter = ("is_active",)
    search_fields = ("id", *DjangoUserAdmin.search_fields, "organisation__name")
    ordering = ("email",)

    fieldsets = (
        (
            "Informations personnelles",
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                )
            },
        ),
        (
            "Informations Technique",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "password",
                )
            },
        ),
        (
            "Informations professionnelles",
            {
                "fields": (
                    "profession",
                    "organisation",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active",)},
        ),
    )

    # `add_fieldsets` is not a standard `ModelAdmin` attribute. `AidantAdmin`
    # overrides `get_fieldsets` to use this attribute when creating an `Aidant`.
    add_fieldsets = (
        (
            "Informations personnelles",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "password",
                )
            },
        ),
    )

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        return qs.filter(is_of_user=True)
