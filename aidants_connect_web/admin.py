from django.contrib.admin import ModelAdmin
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


class VisibleToStaff(ModelAdmin):
    """A mixin to make a model registered in the Admin visible to staff users."""

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


class StaticDeviceStaffAdmin(VisibleToStaff, StaticDeviceAdmin):
    pass


class TOTPDeviceStaffAdmin(VisibleToStaff, TOTPDeviceAdmin):
    pass


class AidantAdmin(VisibleToStaff, DjangoUserAdmin):

    # The forms to add and change aidant instances
    form = AidantChangeForm
    add_form = AidantCreationForm

    # The fields to be used in displaying the `Aidant` model.
    # These override the definitions on the base `UserAdmin`
    # that references specific fields on `auth.User`.
    list_display = ("organisation", "email", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (
            "Informations personnelles",
            {"fields": ("username", "first_name", "last_name", "email", "password")},
        ),
        ("Informations professionnelles", {"fields": ("profession", "organisation")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",)},),
    )
    # `add_fieldsets` is not a standard `ModelAdmin` attribute. `AidantAdmin`
    # overrides `get_fieldsets` to use this attribute when creating an `Aidant`.
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
admin_site.register(Organisation, VisibleToStaff)

admin_site.register(MagicToken)
admin_site.register(StaticDevice, StaticDeviceStaffAdmin)
admin_site.register(TOTPDevice, TOTPDeviceStaffAdmin)
