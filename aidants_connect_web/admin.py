import logging
import operator
from collections import Collection
from functools import reduce

from admin_honeypot.admin import LoginAttemptAdmin as HoneypotLoginAttemptAdmin
from admin_honeypot.models import LoginAttempt as HoneypotLoginAttempt
from django.contrib import messages
from django.contrib.admin import ModelAdmin, TabularInline, SimpleListFilter
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render
from django.urls import reverse, path
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
from django_otp.plugins.otp_static.lib import add_static_token
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
from import_export import resources
from import_export.admin import ImportMixin, ExportMixin, ImportExportMixin
from import_export.fields import Field
from import_export.results import RowResult
from magicauth.models import MagicToken
from nested_admin import NestedModelAdmin, NestedTabularInline
from tabbed_admin import TabbedModelAdmin

from aidants_connect_web.forms import AidantChangeForm, AidantCreationForm
from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    Connection,
    HabilitationRequest,
    Journal,
    Mandat,
    Organisation,
    Usager,
    CarteTOTP,
    DatavizRegion,
    DatavizDepartmentsToRegion,
)

admin_site = OTPAdminSite(OTPAdminSite.name)
admin_site.login_template = "aidants_connect_web/admin/login.html"

admin_site.register(HoneypotLoginAttempt, HoneypotLoginAttemptAdmin)

logger = logging.getLogger()


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


class OrganisationResource(resources.ModelResource):
    name = Field(attribute="name", column_name="Nom de la structure")
    zipcode = Field(attribute="zipcode", column_name="Code postal de la structure")
    siret = Field(attribute="siret", column_name="SIRET de l’organisation")
    status_not_field = Field(
        column_name="Statut de la demande (send = à valider; pending = brouillon)"
    )

    def import_row(
        self,
        row,
        instance_loader,
        using_transactions=True,
        dry_run=False,
        raise_errors=False,
        **kwargs,
    ):
        if (
            row.get(
                "Statut de la demande (send = à valider; pending = brouillon)", None
            )
            == "validated"
        ):
            name = row.get("Nom de la structure", None)
            siret = row.get("SIRET de l’organisation", None)

            if (
                siret
                and name
                and Organisation.objects.filter(name=name, siret=siret).count() == 1
            ):
                return super().import_row(
                    row,
                    instance_loader,
                    using_transactions,
                    dry_run,
                    raise_errors,
                    **kwargs,
                )

        row_result = self.get_row_result_class()()
        row_result.import_type = RowResult.IMPORT_TYPE_SKIP
        return row_result

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        if new:
            instance.skip_new = True

    def skip_row(self, instance, original):
        if getattr(instance, "skip_new", False):
            return True
        if original.zipcode and original.zipcode != "0":
            return True
        return False

    class Meta:
        import_id_fields = (
            "name",
            "siret",
        )
        model = Organisation


class OrganisationRegionFilter(SimpleListFilter):
    title = "Région"

    parameter_name = "region"

    def lookups(self, request, model_admin):
        return [(r.id, r.name) for r in DatavizRegion.objects.all()] + [
            ("other", "Autre")
        ]

    def queryset(self, request, queryset):
        region_id = self.value()

        if not region_id:
            return

        if region_id == "other":
            return queryset.filter(zipcode=0)

        region = DatavizRegion.objects.get(id=region_id)
        d2r = DatavizDepartmentsToRegion.objects.filter(region=region)
        qgroup = reduce(
            operator.or_,
            (Q(zipcode__startswith=d.department.zipcode) for d in d2r.all()),
        )
        return queryset.filter(qgroup)


class OrganisationAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "name",
        "address",
        "siret",
        "zipcode",
        "admin_num_active_aidants",
        "admin_num_mandats",
        "is_active",
        "id",
        "data_pass_id",
    )
    readonly_fields = ("data_pass_id",)
    search_fields = ("name", "siret", "data_pass_id")
    list_filter = ("is_active", OrganisationRegionFilter)

    # For bulk import
    resource_class = OrganisationResource
    change_list_template = (
        "aidants_connect_web/admin/import_export/change_list_organisation_import.html"
    )
    import_template_name = (
        "aidants_connect_web/admin/import_export/import_organisation.html"
    )

    actions = (
        "find_zipcode_in_address",
        "deactivate_organisations",
        "activate_organisations",
    )

    def find_zipcode_in_address(self, request, queryset):
        for organisation in queryset:
            organisation.set_empty_zipcode_from_address()

    def deactivate_organisations(self, request, queryset):
        for organisation in queryset:
            organisation.deactivate_organisation()

    deactivate_organisations.short_description = "Désactiver les organisations"

    def activate_organisations(self, request, queryset):
        for organisation in queryset:
            organisation.activate_organisation()

    activate_organisations.short_description = "Activer les organisations"


class AidantResource(resources.ModelResource):
    organisation_id = Field(attribute="organisation_id", column_name="organisation_id")
    token = Field(attribute="token", column_name="token")
    carte_ac = Field(attribute="carte_ac", column_name="carte_ac")
    carte_totp = Field(attribute="carte_totp", column_name="carte_ac", readonly=True)

    class Meta:
        model = Aidant
        import_id_fields = ("username",)
        fields = (
            "username",
            "last_name",
            "first_name",
            "profession",
            "organisation_id",
            "is_active",
            "responsable_de",
            "carte_ac",
            "can_create_mandats",
        )

    def before_save_instance(self, instance: Aidant, using_transactions, dry_run):
        if not instance.email:
            instance.email = instance.username

    def before_import_row(self, row, row_number=None, **kwargs):
        if row.get("username"):
            row["username"] = row["username"].strip().lower()

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        if row_result.import_type not in (
            RowResult.IMPORT_TYPE_NEW,
            RowResult.IMPORT_TYPE_UPDATE,
        ):
            return

        token = str(row.get("token"))
        if token and len(token) == 6 and token.isnumeric():
            add_static_token(row["username"], token)

    def after_save_instance(self, instance: Aidant, using_transactions, dry_run):
        if hasattr(instance, "carte_ac") and instance.carte_ac is not None:
            card_sn = instance.carte_ac
            # instance.carte_ac is the sn the import added to the aidant instance,
            # it will not be persisted as-is in database.
            if instance.has_a_carte_totp():
                # instance.has_a_carte_totp is true if the aidant is associated with a
                # CarteTOTP in database.
                if instance.carte_totp.serial_number == card_sn:
                    # trying to re-associate the same card: ignore
                    return
                raise Exception(
                    f"L'aidant {instance.username} est déjà lié à la carte "
                    f"{instance.carte_totp.serial_number}, impossible de le lier à "
                    f"la carte {card_sn}."
                )

            try:
                carte_totp = CarteTOTP.objects.get(serial_number=card_sn)
            except CarteTOTP.DoesNotExist:
                raise Exception(
                    f"Le numéro de série {card_sn} ne correspond à aucune carte TOTP"
                    f" (e-mail {instance.username})."
                )
            if carte_totp.aidant:
                raise Exception(
                    f"La carte {card_sn} est déjà liée à l'aidant "
                    f"{carte_totp.aidant.username} : impossible de la lier à "
                    f"{instance.username}."
                )
            carte_totp.aidant = instance
            carte_totp.save()
            totp_device = carte_totp.createTOTPDevice(confirmed=True)
            totp_device.save()


class AidantAdmin(ImportExportMixin, VisibleToAdminMetier, DjangoUserAdmin):
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

    def display_totp_device_status(self, obj):
        return obj.has_a_totp_device()

    display_totp_device_status.short_description = "Carte TOTP Activée"
    display_totp_device_status.boolean = True

    # The forms to add and change `Aidant` instances
    form = AidantChangeForm
    add_form = AidantCreationForm
    raw_id_fields = ("responsable_de", "organisation")
    readonly_fields = (
        "validated_cgu_version",
        "display_totp_device_status",
        "carte_totp",
    )

    # For bulk import
    resource_class = AidantResource
    import_template_name = "aidants_connect_web/admin/import_export/import_aidant.html"

    # The fields to be used in displaying the `Aidant` model.
    # These override the definitions on the base `UserAdmin`
    # that references specific fields on `auth.User`.
    list_display = (
        "__str__",
        "email",
        "organisation",
        "carte_totp",
        "is_active",
        "can_create_mandats",
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
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "password",
                    "carte_totp",
                    "display_totp_device_status",
                )
            },
        ),
        ("Informations professionnelles", {"fields": ("profession", "organisation")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "can_create_mandats",
                    "is_staff",
                    "is_superuser",
                    "responsable_de",
                )
            },
        ),
        ("Aidants Connect", {"fields": ("validated_cgu_version",)}),
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


class HabilitationRequestResource(resources.ModelResource):
    class Meta:
        model = HabilitationRequest
        fields = (
            "first_name",
            "last_name",
            "email",
            "organisation",
            "organisation__name",
            "profession",
            "status",
            "created_at",
            "updated_at",
        )


class HabilitationRequestRegionFilter(SimpleListFilter):
    title = "Région"

    parameter_name = "region"

    def lookups(self, request, model_admin):
        return [(r.id, r.name) for r in DatavizRegion.objects.all()]

    def queryset(self, request, queryset):
        region_id = self.value()

        if not region_id:
            return

        region = DatavizRegion.objects.get(id=region_id)
        d2r = DatavizDepartmentsToRegion.objects.filter(region=region)
        qgroup = reduce(
            operator.or_,
            (
                Q(organisation__zipcode__startswith=d.department.zipcode)
                for d in d2r.all()
            ),
        )
        return queryset.filter(qgroup)


class HabilitationRequestAdmin(ExportMixin, VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "organisation",
        "profession",
        "status",
        "created_at",
    )
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organisation",)
    actions = ("mark_validated", "mark_refused")
    list_filter = ("status", HabilitationRequestRegionFilter)
    search_fields = ("first_name", "last_name", "email", "organisation__name")
    ordering = ("email",)
    resource_class = HabilitationRequestResource

    def mark_validated(self, request, queryset):
        rows_updated = sum(
            1
            for habilitation_request in queryset
            if habilitation_request.validate_and_create_aidant()
        )
        self.message_user(
            request, f"{rows_updated} demandes d'habilitation ont été validées."
        )

    mark_validated.short_description = (
        "Valider les demandes d’habilitation sélectionnées"
    )

    def mark_refused(self, request, queryset):
        rows_updated = queryset.filter(
            status=HabilitationRequest.STATUS_PROCESSING
        ).update(status=HabilitationRequest.STATUS_REFUSED)
        self.message_user(
            request, f"{rows_updated} demandes d’habilitation ont été refusées."
        )

    mark_refused.short_description = "Refuser les demandes d’habilitation sélectionnées"


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

    tab_infos = (("Info", {"fields": ("given_name", "family_name", "email", "phone")}),)
    tab_mandats = (UsagerMandatInline,)

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
    raw_id_fields = ("organisation",)

    inlines = (MandatAutorisationInline,)

    actions = ("move_to_another_organisation",)

    def move_to_another_organisation(self, _, queryset):
        ids = ",".join(
            str(pk) for pk in queryset.order_by("pk").values_list("pk", flat=True)
        )
        return HttpResponseRedirect(
            f"{reverse('otpadmin:aidants_connect_web_mandat_transfer')}?ids={ids}"
        )

    move_to_another_organisation.short_description = (
        "Transférer le mandat vers une autre organisation"
    )

    def get_urls(self):
        return [
            path(
                "transfer/",
                self.admin_site.admin_view(self.mandate_transfer),
                name="aidants_connect_web_mandat_transfer",
            ),
            *super().get_urls(),
        ]

    def get_readonly_fields(self, request, obj=None):
        if isinstance(obj, dict) and isinstance(
            obj.get("exclude_from_readonly_fields", None), Collection
        ):
            readonly_fields = super().get_readonly_fields(request, obj)
            return [
                field
                for field in readonly_fields
                if field not in obj["exclude_from_readonly_fields"]
            ]
        else:
            return super().get_readonly_fields(request, obj)

    def mandate_transfer(self, request):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__mandate_transfer_get(request)
        else:
            return self.__mandate_transfer_post(request)

    def __mandate_transfer_get(self, request):
        ids: str = request.GET.get("ids")
        if not ids:
            self.message_user(
                request,
                "Des mandats doivent être sélectionnés afin d’appliquer un transfert. "
                "Aucun élément n’a été transféré.",
                messages.ERROR,
            )

            return HttpResponseRedirect(
                reverse("otpadmin:aidants_connect_web_mandat_changelist")
            )

        include_fields = ["organisation"]
        mandates = Mandat.objects.filter(pk__in=ids.split(","))
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "form": self.get_form(
                request,
                obj={"exclude_from_readonly_fields": include_fields},
                fields=include_fields,
            ),
            "ids": ids,
            "mandates": mandates,
            "mandates_count": mandates.count(),
        }

        return render(request, "admin/transfert.html", context)

    def __mandate_transfer_post(self, request):
        try:
            ids = request.POST["ids"].split(",")
            organisation = Organisation.objects.get(pk=request.POST["organisation"])
            failure, failed_ids = Mandat.transfer_to_organisation(organisation, ids)

            mandates = Mandat.objects.filter(pk__in=failed_ids)
            if failure:
                context = {
                    **self.admin_site.each_context(request),
                    "media": self.media,
                    "mandates": mandates,
                    "mandates_count": mandates.count(),
                }

                return render(request, "admin/transfert_error.html", context)
        except Organisation.DoesNotExist:
            self.message_user(
                request,
                "L'organisation sélectionnée n'existe pas. "
                "Veuillez corriger votre requête",
                messages.ERROR,
            )

            return HttpResponseRedirect(
                f"{reverse('otpadmin:aidants_connect_web_mandat_transfer')}"
                f"?ids={request.POST['ids']}"
            )
        except Exception:
            logger.exception(
                "An error happened while trying to transfer mandates to "
                "another organisation"
            )

            self.message_user(
                request,
                "Les mandats n'ont pas pu être tansférés à cause d'une erreur.",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("otpadmin:aidants_connect_web_mandat_changelist")
        )


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


class CarteTOTPResource(resources.ModelResource):
    class Meta:
        model = CarteTOTP
        import_id_fields = ("serial_number",)
        fields = ("serial_number", "seed")


class CarteTOTPAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
    list_display = ("serial_number", "aidant")
    search_fields = ("serial_number",)
    raw_id_fields = ("aidant",)
    ordering = ("-created_at",)
    resource_class = CarteTOTPResource
    import_template_name = "aidants_connect_web/admin/import_export/import.html"

    def generate_log_entries(self, result, request):
        super().generate_log_entries(result, request)
        Journal.log_toitp_card_import(
            request.user,
            result.totals[RowResult.IMPORT_TYPE_NEW],
            result.totals[RowResult.IMPORT_TYPE_UPDATE],
        )


# Display the following tables in the admin
admin_site.register(Organisation, OrganisationAdmin)
admin_site.register(Aidant, AidantAdmin)
admin_site.register(HabilitationRequest, HabilitationRequestAdmin)
admin_site.register(Usager, UsagerAdmin)
admin_site.register(Mandat, MandatAdmin)
admin_site.register(Journal, JournalAdmin)
admin_site.register(Connection, ConnectionAdmin)

admin_site.register(MagicToken)
admin_site.register(StaticDevice, StaticDeviceStaffAdmin)
admin_site.register(TOTPDevice, TOTPDeviceStaffAdmin)
admin_site.register(CarteTOTP, CarteTOTPAdmin)

# Also register the Django Celery Beat models
admin_site.register(PeriodicTask, PeriodicTaskAdmin)
admin_site.register(IntervalSchedule)
admin_site.register(CrontabSchedule)
admin_site.register(SolarSchedule)
admin_site.register(ClockedSchedule, ClockedScheduleAdmin)
