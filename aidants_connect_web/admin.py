from admin_honeypot.admin import LoginAttemptAdmin as HoneypotLoginAttemptAdmin
from admin_honeypot.models import LoginAttempt as HoneypotLoginAttempt
from django.contrib.admin import ModelAdmin, TabularInline
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
from nested_admin import NestedModelAdmin, NestedTabularInline
from tabbed_admin import TabbedModelAdmin

from aidants_connect_web.forms import AidantChangeForm, AidantCreationForm
from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    Connection,
    Journal,
    Mandat,
    Organisation,
    Usager,
)

admin_site = OTPAdminSite(OTPAdminSite.name)
admin_site.login_template = "aidants_connect_web/admin/login.html"

admin_site.register(HoneypotLoginAttempt, HoneypotLoginAttemptAdmin)


class VisibleToAdminMetier:
    """A mixin to make a model registered in the Admin visible to Admin Métier.
       Admin Métier corresponds to the traditional django `is_staff`
    """

    def has_module_permission(self, request):
        return request.user.is_staff or request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


class VisibleToTechAdmin:
    """A mixin to make a model registered in the Admin visible to Tech Admins.
        ATAC is modelised by is_superuser
    """

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


class StaticDeviceStaffAdmin(VisibleToAdminMetier, StaticDeviceAdmin):
    pass


class TOTPDeviceStaffAdmin(VisibleToAdminMetier, TOTPDeviceAdmin):
    pass


class OrganisationAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = ("name",
                    "address",
                    "admin_num_active_aidants",
                    "admin_num_mandats")
    search_fields = ("name",)


class AidantAdmin(VisibleToAdminMetier, DjangoUserAdmin):
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
    list_display = (
        "__str__",
        "email",
        "organisation",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("first_name", "last_name", "email", "organisation__name")
    ordering = ("email",)

    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (
            "Informations personnelles",
            {"fields": ("username", "first_name", "last_name", "email", "password")},
        ),
        ("Informations professionnelles", {"fields": ("profession", "organisation")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
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


class UsagerAdmin(VisibleToTechAdmin, NestedModelAdmin, TabbedModelAdmin):
    list_display = ("__str__", "email", "creation_date")
    search_fields = ("given_name", "family_name", "email")

    tab_infos = (None, {"fields": ("given_name", "family_name", "email")})

    tab_mandats = UsagerMandatInline

    tabs = [("Informations", tab_infos), ("Mandats", tab_mandats)]


class MandatAutorisationInline(VisibleToTechAdmin, TabularInline):
    model = Autorisation
    fields = ("demarche", "revocation_date")
    readonly_fields = fields
    extra = 0
    max_num = 0


class MandatAdmin(VisibleToTechAdmin, ModelAdmin):
    list_display = (
        "id",
        "usager",
        "organisation",
        "creation_date",
        "expiration_date",
        "admin_is_active",
        "is_remote",
    )
    list_filter = ("organisation",)
    search_fields = ("usager__given_name", "usager__family_name", "organisation__name")

    fields = (
        "usager",
        "organisation",
        "duree_keyword",
        "creation_date",
        "expiration_date",
        "admin_is_active",
        "is_remote",
    )

    readonly_fields = fields

    inlines = (MandatAutorisationInline,)


class ConnectionAdmin(ModelAdmin):
    list_display = ("id", "usager", "aidant", "complete")


class JournalAdmin(VisibleToTechAdmin, ModelAdmin):
    list_display = ("id", "action", "aidant", "creation_date")
    list_filter = ("action", "aidant")
    search_fields = ("action", "aidant")
    ordering = ("-creation_date",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Display the following tables in the admin
admin_site.register(Organisation, OrganisationAdmin)
admin_site.register(Aidant, AidantAdmin)
admin_site.register(Usager, UsagerAdmin)
admin_site.register(Mandat, MandatAdmin)
admin_site.register(Journal, JournalAdmin)
admin_site.register(Connection, ConnectionAdmin)

admin_site.register(MagicToken)
admin_site.register(StaticDevice, StaticDeviceStaffAdmin)
admin_site.register(TOTPDevice, TOTPDeviceStaffAdmin)

# Also register the Django Celery Beat models
admin_site.register(PeriodicTask, PeriodicTaskAdmin)
admin_site.register(IntervalSchedule)
admin_site.register(CrontabSchedule)
admin_site.register(SolarSchedule)
admin_site.register(ClockedSchedule, ClockedScheduleAdmin)
