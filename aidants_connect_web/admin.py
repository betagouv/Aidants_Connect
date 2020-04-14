from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from django_celery_beat.admin import (
    ClockedScheduleAdmin,
    PeriodicTaskAdmin,
)
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)

from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_static.admin import StaticDeviceAdmin
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice

from magicauth.models import MagicToken

from aidants_connect_web.forms import AidantChangeForm, AidantCreationForm
from aidants_connect_web.models import (
    Aidant,
    Connection,
    Journal,
    Mandat,
    Organisation,
    Usager,
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
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Prevent non-superusers from being able to set
        # the `is_staff` and `is_superuser` flags.
        if not request.user.is_superuser:
            if "is_superuser" in form.base_fields:
                form.base_fields["is_superuser"].disabled = True
            if "is_staff" in form.base_fields:
                form.base_fields["is_staff"].disabled = True

        return form

    # The forms to add and change `Aidant` instances
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


class UsagerAdmin(ModelAdmin):
    list_display = ("__str__", "email", "creation_date")
    search_fields = ("given_name", "family_name", "email")


class MandatAdmin(ModelAdmin):
    list_display = (
        "id",
        "usager",
        "aidant",
        "demarche",
        "creation_date",
        "expiration_date",
        "is_remote_mandat",
    )
    list_filter = ("demarche",)
    search_fields = ("usager", "aidant", "demarche")


class JournalAdmin(ModelAdmin):
    list_display = ("id", "action", "initiator", "creation_date")
    list_filter = ("action",)
    search_fields = ("action", "initiator")
    ordering = ("-creation_date",)


class ConnectionAdmin(ModelAdmin):
    list_display = ("id", "usager", "aidant", "complete")


# Display the following tables in the admin
admin_site.register(Aidant, AidantAdmin)
admin_site.register(Usager, UsagerAdmin)
admin_site.register(Mandat, MandatAdmin)
admin_site.register(Journal, JournalAdmin)
admin_site.register(Connection, ConnectionAdmin)
admin_site.register(Organisation, VisibleToStaff)

admin_site.register(MagicToken)
admin_site.register(StaticDevice, StaticDeviceAdmin)
admin_site.register(TOTPDevice, TOTPDeviceAdmin)


# Also register the Django Celery Beat models
admin_site.register(PeriodicTask, PeriodicTaskAdmin)
admin_site.register(IntervalSchedule)
admin_site.register(CrontabSchedule)
admin_site.register(SolarSchedule)
admin_site.register(ClockedSchedule, ClockedScheduleAdmin)
