from django.contrib import admin
from aidants_connect_web.forms import AidantChangeForm, AidantCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from aidants_connect_web.models import Aidant, Usager, Mandat, Journal, Connection


class AidantAdmin(DjangoUserAdmin):
    # The forms to add and change aidant instances
    form = AidantChangeForm
    add_form = AidantCreationForm

    # The fields to be used in displaying the Aidant model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ("email", "is_superuser", "organisation")
    list_filter = ("is_superuser",)
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (
            "Informations personnelles",
            {"fields": ("username", "first_name", "last_name", "email", "password")},
        ),
        ("Informations professionnelles", {"fields": ("profession", "organisation")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. AidantAdmin
    # overrides get_fieldsets to use this attribute when creating an aidant.
    add_fieldsets = (
        (
            "Informations personnelles",
            {"fields": ("first_name", "last_name", "email", "password", "username")},
        ),
        ("Informations professionnelles", {"fields": ("profession", "organisation")}),
    )
    search_fields = ("email", "organisation")
    ordering = ("email",)


# Now register the new AidantAdmin...
admin.site.register(Aidant, AidantAdmin)
admin.site.register(Usager)
admin.site.register(Mandat)
admin.site.register(Journal)
admin.site.register(Connection)

# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)
