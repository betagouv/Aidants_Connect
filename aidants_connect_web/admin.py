from django.contrib import admin
from aidants_connect_web.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from aidants_connect_web.models import User, Usager, Mandat


class UserAdmin(DjangoUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ("email", "is_superuser", "organisme")
    list_filter = ("is_superuser",)
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (
            "Informations personnelles",
            {"fields": ("username", "first_name", "last_name", "email", "password")},
        ),
        (
            "Informations professionnelles",
            {"fields": ("profession", "organisme", "ville")},
        ),
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
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            "Informations personnelles",
            {"fields": ("first_name", "last_name", "email", "password", "username")},
        ),
        (
            "Informations professionnelles",
            {"fields": ("profession", "organisme", "ville")},
        ),
    )
    search_fields = ("email", "organisme")
    ordering = ("email",)


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
admin.site.register(Usager)
admin.site.register(Mandat)
# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)
