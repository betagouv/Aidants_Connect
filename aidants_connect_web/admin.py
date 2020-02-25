from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_static.admin import StaticDeviceAdmin
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice

from magicauth.models import MagicToken

from aidants_connect_web.forms import AidantChangeForm, AidantCreationForm
from aidants_connect_web.models import (
    Aidant,
    Usager,
    Mandat,
    Journal,
    Connection,
    Organisation,
)


admin_site = OTPAdminSite(OTPAdminSite.name)


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


# Display the following tables in the admin
admin_site.register(Aidant, AidantAdmin)
admin_site.register(Usager)
admin_site.register(Mandat)
admin_site.register(Journal)
admin_site.register(Connection)
admin_site.register(Organisation)

admin_site.register(MagicToken)
admin_site.register(StaticDevice, StaticDeviceAdmin)
admin_site.register(TOTPDevice, TOTPDeviceAdmin)
