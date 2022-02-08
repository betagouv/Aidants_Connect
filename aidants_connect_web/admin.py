import logging
from collections.abc import Collection

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin, TabularInline, SimpleListFilter
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import QuerySet
from django.http import HttpResponseRedirect, HttpResponseNotAllowed, HttpRequest
from django.shortcuts import render
from django.urls import reverse, path
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from django_otp.plugins.otp_static.admin import StaticDeviceAdmin
from django_otp.plugins.otp_static.lib import add_static_token
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
from import_export import resources
from import_export.admin import ImportMixin, ImportExportMixin
from import_export.fields import Field
from import_export.results import RowResult
from import_export.widgets import ManyToManyWidget, ForeignKeyWidget
from nested_admin import NestedModelAdmin, NestedTabularInline
from tabbed_admin import TabbedModelAdmin

from aidants_connect.admin import (
    admin_site,
    VisibleToAdminMetier,
    VisibleToTechAdmin,
    DepartmentFilter,
    RegionFilter,
)
from aidants_connect_web.forms import (
    AidantChangeForm,
    AidantCreationForm,
    MassEmailHabilitatonForm,
)
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
)

logger = logging.getLogger()


class StaticDeviceStaffAdmin(VisibleToAdminMetier, StaticDeviceAdmin):
    pass


class TOTPDeviceStaffAdmin(VisibleToAdminMetier, TOTPDeviceAdmin):
    pass


class OrganisationResource(resources.ModelResource):
    datapass_id = Field(attribute="data_pass_id", column_name="Numéro de demande")
    name = Field(attribute="name", column_name="Nom de la structure")
    zipcode = Field(attribute="zipcode", column_name="Code postal de la structure")
    city = Field(attribute="city", column_name="Ville de la structure")
    siret = Field(attribute="siret", column_name="SIRET de l’organisation")
    status_not_field = Field(
        column_name="Statut de la demande (send = à valider; pending = brouillon)"
    )

    def import_field(self, field, obj, data, is_m2m=False):
        """
        Calls :meth:`import_export.fields.Field.save` if ``Field.attribute``
        and ``Field.column_name`` are found in ``data``.
        """
        if field.attribute == "zipcode":
            if not obj.zipcode or obj.zipcode == "0":
                field.save(obj, data, is_m2m)
        elif field.attribute == "city":
            if not obj.city:
                field.save(obj, data, is_m2m)
        elif field.attribute == "data_pass_id":
            if not obj.data_pass_id or obj.data_pass_id == 0:
                field.save(obj, data, is_m2m)
        else:
            super().import_field(field, obj, data, is_m2m)

    def import_row(
        self,
        row,
        instance_loader,
        using_transactions=True,
        dry_run=False,
        raise_errors=False,
        **kwargs,
    ):
        name_row = "Statut de la demande (send = à valider; pending = brouillon)"
        if row.get(name_row, None) == "validated":
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
        if original.data_pass_id and original.data_pass_id != instance.data_pass_id:
            return True
        return False

    class Meta:
        import_id_fields = (
            "name",
            "siret",
        )
        model = Organisation


class WithoutDatapassIdFilter(SimpleListFilter):
    title = "Numéro de demande Datapass"

    parameter_name = "datapass_id"

    def lookups(self, request, model_admin):
        return (("without", "Sans n° Datapass"),)

    def queryset(self, request, queryset):
        datapass_id = self.value()

        if not datapass_id:
            return

        if datapass_id == "without":
            return queryset.filter(data_pass_id=None)


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
    readonly_fields = (
        "display_responsables",
        "display_aidants",
        "display_habilitation_requests",
    )
    search_fields = ("name", "siret", "data_pass_id")
    list_filter = (
        "is_active",
        WithoutDatapassIdFilter,
        RegionFilter,
        DepartmentFilter,
    )

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

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.data_pass_id:
            readonly_fields.append("data_pass_id")
        return readonly_fields

    def display_responsables(self, obj):
        return self.format_list_of_aidants(obj.responsables.order_by("last_name").all())

    display_responsables.short_description = "Responsables"

    def display_aidants(self, obj):
        return self.format_list_of_aidants(obj.aidants.order_by("last_name").all())

    display_aidants.short_description = "Aidants"

    def format_list_of_aidants(self, aidants_list):
        return mark_safe(
            "<table><tr>"
            + '<th scope="col">id</th><th scope="col">Nom</th><th>E-mail</th></tr><tr>'
            + "</tr><tr>".join(
                '<td>{}</td><td><a href="{}">{}</a></td><td>{}</td>'.format(
                    aidant.id,
                    reverse(
                        "otpadmin:aidants_connect_web_aidant_change",
                        kwargs={"object_id": aidant.id},
                    ),
                    aidant,
                    aidant.email,
                )
                for aidant in aidants_list
            )
            + "</tr></table>"
        )

    def display_habilitation_requests(self, obj):
        headers = ("Id", "Nom", "Prénom", "Email", "Origine", "État")
        return mark_safe(
            '<table><tr><th scope="col">'
            + '</th><th scope="col">'.join(headers)
            + "</th></tr><tr><td>"
            + "</td></tr><tr><td>".join(
                "</td><td>".join(
                    (
                        str(hr.id),
                        hr.last_name,
                        hr.first_name,
                        hr.email,
                        hr.origin_label,
                        hr.status_label,
                    )
                )
                for hr in obj.habilitation_requests.order_by("last_name").all()
            )
            + "</td></tr></table>"
        )

    display_habilitation_requests.short_description = "Aidants à former"

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
    datapass_id = Field(
        attribute="organisation",
        widget=ForeignKeyWidget(Organisation, field="data_pass_id"),
    )
    responsable_de = Field(
        attribute="responsable_de",
        widget=ManyToManyWidget(Organisation, separator=";"),
    )
    respo_de_datapass_id = Field(
        attribute="responsable_de",
        widget=ManyToManyWidget(Organisation, field="data_pass_id", separator=";"),
    )

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
            "phone",
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
            if instance.has_a_carte_totp:
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


class AidantDepartmentFilter(DepartmentFilter):
    filter_parameter_name = "organisations__zipcode"


class AidantRegionFilter(RegionFilter):
    filter_parameter_name = "organisations__zipcode"


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
        return obj.has_a_totp_device

    display_totp_device_status.short_description = "Carte TOTP Activée"
    display_totp_device_status.boolean = True

    # The forms to add and change `Aidant` instances
    form = AidantChangeForm
    add_form = AidantCreationForm
    actions = ["mass_deactivate"]
    raw_id_fields = ("responsable_de", "organisation", "organisations")
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
    list_filter = (
        "is_active",
        AidantRegionFilter,
        AidantDepartmentFilter,
        "is_staff",
        "is_superuser",
    )
    search_fields = ("first_name", "last_name", "email", "organisation__name")
    ordering = ("email",)

    filter_horizontal = (
        "groups",
        "user_permissions",
    )
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
                    "password",
                    "carte_totp",
                    "display_totp_device_status",
                )
            },
        ),
        (
            "Informations professionnelles",
            {
                "fields": (
                    "profession",
                    "organisation",
                    "organisations",
                )
            },
        ),
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
        (
            "Informations professionnelles",
            {
                "fields": (
                    "profession",
                    "organisation",
                    "organisations",
                )
            },
        ),
    )

    # Ugh… When you save a model via admin forms it's not an atomic transaction.
    # So… You need to override save_related… https://stackoverflow.com/a/1925784
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        organisation = form.cleaned_data["organisation"]
        if organisation is not None:
            form.instance.organisations.add(organisation)

    def mass_deactivate(self, request: HttpRequest, queryset: QuerySet):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} profils ont été désactivés")

    mass_deactivate.short_description = "Désactiver les profils sélectionnés"


class HabilitationRequestResource(resources.ModelResource):
    created_at = Field(attribute="created_at", column_name="Date d'ajout")
    organisation__data_pass_id = Field(
        attribute="organisation__data_pass_id", column_name="N° de la demande Datapass"
    )
    organisation__name = Field(
        attribute="organisation__name", column_name="Nom de la structure"
    )
    organisation__type__name = Field(
        attribute="organisation__type__name", column_name="Type de structure"
    )
    responsable__last_name = Field(
        attribute="organisation__responsables",
        column_name="Responsable Aidants Connect (Nom)",
        widget=ManyToManyWidget(Aidant, field="last_name", separator="\n"),
    )
    responsable__first_name = Field(
        attribute="organisation__responsables",
        column_name="Responsable Aidants Connect (Prénom)",
        widget=ManyToManyWidget(Aidant, field="first_name", separator="\n"),
    )
    responsable__profession = Field(
        attribute="organisation__responsables",
        column_name="Intitulé de poste du responsable Aidants Connect",
        widget=ManyToManyWidget(Aidant, field="profession", separator="\n"),
    )
    reponsable__email = Field(
        attribute="organisation__responsables",
        column_name="Responsable Aidants Connect (adresse mail)",
        widget=ManyToManyWidget(Aidant, field="email", separator="\n"),
    )
    responsable__phone = Field(
        attribute="organisation__responsables",
        column_name="Téléphone responsable Aidants Connect",
        widget=ManyToManyWidget(Aidant, field="phone", separator="\n"),
    )
    last_name = Field(attribute="last_name", column_name="Nom de l'aidant à former")
    first_name = Field(
        attribute="first_name", column_name="Prénom de l'aidant à former"
    )
    email = Field(attribute="email", column_name="Adresse e-mail de l'aidant à former")
    profession = Field(
        attribute="profession", column_name="Intitulé de poste de l'aidant à former"
    )
    organisation__address = Field(
        attribute="organisation__address", column_name="Adresse Postale"
    )
    organisation__zipcode = Field(
        attribute="organisation__zipcode", column_name="Code Postal"
    )
    organisation__city = Field(attribute="", column_name="Ville")
    organisation__departement = Field(attribute="", column_name="Département")
    organisation__region = Field(attribute="", column_name="Région")

    class Meta:
        model = HabilitationRequest
        fields = set()


class HabilitationRequestImportResource(resources.ModelResource):
    organisation__data_pass_id = Field(
        attribute="organisation",
        widget=ForeignKeyWidget(Organisation, field="data_pass_id"),
        column_name="data_pass_id",
    )
    last_name = Field(attribute="last_name")
    first_name = Field(attribute="first_name")
    email = Field(attribute="email")
    profession = Field(attribute="profession")
    status = Field(attribute="status")
    origin = Field(attribute="origin")

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        if new:
            instance.is_new = True

    def skip_row(self, instance, original):
        # do not change existing rows in database
        return not getattr(instance, "is_new", False)

    class Meta:
        model = HabilitationRequest
        fields = set()
        import_id_fields = ("email", "organisation__data_pass_id")


class HabilitationDepartmentFilter(DepartmentFilter):
    filter_parameter_name = "organisation__zipcode"


class HabilitationRequestRegionFilter(RegionFilter):
    filter_parameter_name = "organisation__zipcode"


class HabilitationRequestAdmin(ImportExportMixin, VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "organisation",
        "display_datapass_id",
        "profession",
        "status",
        "created_at",
    )
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organisation",)
    actions = ("mark_validated", "mark_refused", "mark_processing")
    list_filter = (
        "status",
        "origin",
        HabilitationRequestRegionFilter,
        HabilitationDepartmentFilter,
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "organisation__name",
        "organisation__data_pass_id",
    )
    ordering = ("email",)

    # Change resource class if explicit setting is set
    resource_class = HabilitationRequestResource
    if settings.AC_IMPORT_HABILITATION_REQUESTS:
        resource_class = HabilitationRequestImportResource

    change_list_template = (
        "aidants_connect_web/admin/habilitation_request/change_list.html"
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("organisation")

    def display_datapass_id(self, obj):
        if obj.organisation:
            return obj.organisation.data_pass_id

    display_datapass_id.short_description = "N° Datapass"

    def mark_validated(self, request, queryset):
        rows_updated = sum(
            1
            for habilitation_request in queryset
            if habilitation_request.validate_and_create_aidant()
        )
        self.message_user(request, f"{rows_updated} demandes ont été validées.")

    mark_validated.short_description = "Créer les comptes aidants sélectionnés"

    def mark_refused(self, request, queryset):
        rows_updated = queryset.filter(
            status__in=(
                HabilitationRequest.STATUS_PROCESSING,
                HabilitationRequest.STATUS_NEW,
            )
        ).update(status=HabilitationRequest.STATUS_REFUSED)
        self.message_user(request, f"{rows_updated} demandes ont été refusées.")

    mark_refused.short_description = "Refuser les demandes sélectionnées"

    def mark_processing(self, request, queryset):
        rows_updated = queryset.filter(status=HabilitationRequest.STATUS_NEW).update(
            status=HabilitationRequest.STATUS_PROCESSING
        )
        self.message_user(request, f"{rows_updated} demandes sont maintenant en cours.")

    mark_processing.short_description = "Passer « en cours » les demandes sélectionnées"

    def get_urls(self):
        return [
            path(
                "validate-from-emails/",
                self.admin_site.admin_view(self.validate_from_email),
                name="aidants_connect_web_habilitation_request_mass_validate",
            ),
            *super().get_urls(),
        ]

    def validate_from_email(self, request):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__validate_from_email_get(request)
        else:
            return self.__validate_from_email_post(request)

    def __validate_from_email_get(self, request):
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "form": MassEmailHabilitatonForm(),
        }

        return render(
            request,
            "aidants_connect_web/admin/habilitation_request/mass-habilitation.html",
            context,
        )

    def __validate_from_email_post(self, request):
        form = MassEmailHabilitatonForm(request.POST)
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "form": form,
        }
        if not form.is_valid():
            return render(
                request,
                "aidants_connect_web/admin/habilitation_request/mass-habilitation.html",
                context,
            )
        email_list = form.cleaned_data.get("email_list")
        valid_habilitation_requests = HabilitationRequest.objects.filter(
            email__in=email_list
        ).filter(
            status__in=(
                HabilitationRequest.STATUS_PROCESSING,
                HabilitationRequest.STATUS_NEW,
            )
        )
        treated_emails = set()
        for habilitation_request in valid_habilitation_requests:
            if habilitation_request.validate_and_create_aidant():
                treated_emails.add(habilitation_request.email)
        if len(email_list) > 0 and len(treated_emails) == len(email_list):
            self.message_user(
                request,
                f"Les {len(treated_emails)} demandes ont bien été validées.",
                messages.SUCCESS,
            )
            return HttpResponseRedirect(
                reverse("otpadmin:aidants_connect_web_habilitationrequest_changelist")
            )
        context["treated_emails"] = treated_emails
        context["ignored_emails"] = email_list - treated_emails
        return render(
            request,
            "aidants_connect_web/admin/habilitation_request/mass-habilitation.html",
            context,
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

    tab_infos = (("Info", {"fields": ("given_name", "family_name", "email", "phone")}),)
    tab_mandats = (UsagerMandatInline,)

    tabs = [("Informations", tab_infos), ("Mandats", tab_mandats)]
    actions = ("specific_deleted_action",)

    def get_actions(self, request):
        actions = super(UsagerAdmin, self).get_actions(request)
        try:
            del actions["delete_selected"]
        except KeyError:
            pass
        return actions

    def specific_deleted_action(self, request, queryset):
        for usager in queryset:
            usager.clean_journal_entries_and_delete_mandats()
            usager.delete()

    specific_deleted_action.short_description = "Supprimer les usagers sélectionnés"


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
        readonly_fields = super().get_readonly_fields(request, obj)

        if not (
            isinstance(obj, dict)
            and isinstance(obj.get("exclude_from_readonly_fields"), Collection)
        ):
            return readonly_fields

        return set(readonly_fields) - set(obj["exclude_from_readonly_fields"])

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
    list_display = (
        "creation_date",
        "action",
        "aidant",
        "usager",
        "additional_information",
        "id",
    )
    list_filter = ("action",)

    search_fields = (
        "action",
        "aidant__first_name",
        "aidant__last_name",
        "aidant__email",
        "usager__family_name",
        "usager__given_name",
        "usager__email",
        "additional_information",
    )
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
    def totp_devices_diagnostic(self, obj):
        devices = TOTPDevice.objects.filter(key=obj.seed)

        aidant_id = 0
        if obj.aidant is not None:
            aidant_id = obj.aidant.id

        if devices.count() == 0:
            if aidant_id > 0:
                return mark_safe(
                    "🚨 Aucun device ne correspond à cette carte. <br>"
                    "Pour régler le problème : cliquer sur le bouton "
                    "« Créer un TOTP Device manquant » en haut de cette page."
                )
            else:
                return "✅ Tout va bien !"

        if devices.count() == 1:
            device = devices.first()
            device_url = reverse(
                "otpadmin:otp_totp_totpdevice_change",
                kwargs={"object_id": device.id},
            )
            if aidant_id == 0:
                return mark_safe(
                    f"🚨 Cette carte devrait être associée à l’aidant {device.user} : "
                    f"saisir {device.user.id} dans le champ ci-dessus puis Enregistrer."
                    f'<br><a href="{device_url}">Voir le device {device.name}</a>'
                )
            elif aidant_id != device.user.id:
                return mark_safe(
                    f"🚨 Cette carte est assignée à l'aidant {obj.aidant}, "
                    f"mais le device est assigné à {device.user}."
                    f'<br><a href="{device_url}">Voir le device {device.name}</a>'
                )
            else:
                return mark_safe(
                    "✅ Tout va bien !"
                    f'<br><a href="{device_url}">Voir le device {device.name}</a>'
                )

        return (
            mark_safe(
                "<p>🚨 Il faudrait garder un seul TOTP Device parmi ceux-ci :</p>"
                '<table><tr><th scope="col">ID</th>'
                '<th scope="col">Nom</th>'
                '<th scope="col">Confirmé</th>'
                '<th scope="col">Aidant</th>'
                '<th scope="col">ID Aidant</th></tr>'
            )
            + format_html_join(
                "",
                (
                    '<tr><td>{}</td><td><a href="{}">{}</a></td><td>{}</td>'
                    "<td>{}</td><td>{}</td></tr>"
                ),
                (
                    (
                        d.id,
                        reverse(
                            "otpadmin:otp_totp_totpdevice_change",
                            kwargs={"object_id": d.id},
                        ),
                        d.name,
                        f"{'Oui' if d.confirmed else 'Non'}",
                        d.user,
                        f"{'🚨' if d.user.id != aidant_id else '✅'} {d.user.id}",
                    )
                    for d in devices
                ),
            )
            + mark_safe("</table>")
        )

    totp_devices_diagnostic.short_description = "Diagnostic Carte/TOTP Device"

    list_display = ("serial_number", "aidant")
    search_fields = ("serial_number",)
    raw_id_fields = ("aidant",)
    readonly_fields = ("totp_devices_diagnostic",)
    ordering = ("-created_at",)
    resource_class = CarteTOTPResource
    import_template_name = "aidants_connect_web/admin/import_export/import.html"
    change_form_template = "aidants_connect_web/admin/carte_totp/change_form.html"

    def generate_log_entries(self, result, request):
        super().generate_log_entries(result, request)
        Journal.log_toitp_card_import(
            request.user,
            result.totals[RowResult.IMPORT_TYPE_NEW],
            result.totals[RowResult.IMPORT_TYPE_UPDATE],
        )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/dissociate_from_aidant/",
                self.admin_site.admin_view(self.dissociate_from_aidant),
                name="aidants_connect_web_carte_totp_dissociate",
            ),
            path(
                "<path:object_id>/associate_to_aidant/",
                self.admin_site.admin_view(self.associate_to_aidant),
                name="aidants_connect_web_carte_totp_associate",
            ),
            *super().get_urls(),
        ]

    def associate_to_aidant(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__associate_to_aidant_get(request, object_id)
        else:
            return self.__associate_to_aidant_post(request, object_id)

    def dissociate_from_aidant(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__dissociate_from_aidant_get(request, object_id)
        else:
            return self.__dissociate_from_aidant_post(request, object_id)

    def __associate_to_aidant_get(self, request, object_id):
        object = CarteTOTP.objects.get(id=object_id)
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
            "form": self.get_form(request, fields=["aidant"], obj=object),
        }

        return render(
            request, "aidants_connect_web/admin/carte_totp/associate.html", context
        )

    def __associate_to_aidant_post(self, request, object_id):
        def redirect_to_list():
            return HttpResponseRedirect(
                reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
            )

        def redirect_to_object(object_id):
            return HttpResponseRedirect(
                reverse(
                    "otpadmin:aidants_connect_web_cartetotp_change",
                    kwargs={"object_id": object_id},
                )
            )

        def redirect_to_try_again(object_id):
            return HttpResponseRedirect(
                reverse(
                    "otpadmin:aidants_connect_web_carte_totp_associate",
                    kwargs={"object_id": object_id},
                )
            )

        if request.POST["aidant"].isnumeric():
            target_aidant_id = int(request.POST["aidant"])
        else:
            self.message_user(
                request, "L'identifiant de l'aidant est obligatoire.", messages.ERROR
            )
            return redirect_to_try_again(object_id)
        carte = CarteTOTP.objects.get(id=object_id)

        try:
            # Check if we are trying to associate the card with another aidant: BAD
            if carte.aidant is not None:
                if target_aidant_id != carte.aidant.id:
                    self.message_user(
                        request,
                        f"La carte {carte} est déjà associée à un autre aidant.",
                        messages.ERROR,
                    )
                    return redirect_to_list()

            # link card with aidant
            target_aidant = Aidant.objects.get(id=target_aidant_id)
            if target_aidant.has_a_carte_totp and carte.aidant != target_aidant:
                self.message_user(
                    request,
                    f"L’aidant {target_aidant} a déjà une carte TOTP. "
                    "Vous ne pouvez pas le lier à celle-ci en plus.",
                    messages.ERROR,
                )
                return redirect_to_try_again(object_id)
            carte.aidant = target_aidant
            carte.save()

            # check if totp devices need to be created
            totp_devices = TOTPDevice.objects.filter(user=target_aidant, key=carte.seed)
            if totp_devices.count() > 0:
                self.message_user(
                    request, "Tout s'est bien passé. Le TOTP Device existait déjà."
                )
                return redirect_to_object(object_id)
            else:
                # No Device exists: crate the TOTP Device and save everything
                new_device = carte.createTOTPDevice(confirmed=True)
                new_device.save()
                Journal.log_card_association(
                    request.user, target_aidant, carte.serial_number
                )
                self.message_user(
                    request,
                    f"Tout s'est bien passé. La carte {carte} a été associée à "
                    f"{target_aidant} et un TOTP Device a été créé.",
                )
                return redirect_to_list()

        except Aidant.DoesNotExist:
            self.message_user(
                request,
                f"Aucun aidant n’existe avec l'ID {target_aidant_id}. "
                "Veuillez corriger votre saisie.",
                messages.ERROR,
            )
            return redirect_to_try_again(object_id)
        except Exception as e:
            logger.exception(
                "An error occured while trying to associate an aidant"
                "with a new TOTP."
            )
            self.message_user(
                request,
                f"Quelque chose s’est mal passé durant l'opération. {e}",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
        )

    def __dissociate_from_aidant_get(self, request, object_id):
        object = CarteTOTP.objects.get(id=object_id)
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
        }

        return render(
            request, "aidants_connect_web/admin/carte_totp/dissociate.html", context
        )

    def __dissociate_from_aidant_post(self, request, object_id):
        try:
            object = CarteTOTP.objects.get(id=object_id)
            aidant = object.aidant
            if aidant is None:
                self.message_user(
                    request,
                    f"Aucun aidant n’est associé à la carte {object.serial_number}.",
                    messages.ERROR,
                )
                return HttpResponseRedirect(
                    reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
                )

            totp_devices = TOTPDevice.objects.filter(user=aidant, key=object.seed)
            for d in totp_devices:
                d.delete()
            object.aidant = None
            object.save()

            Journal.log_card_dissociation(
                request.user, aidant, object.serial_number, "Admin action"
            )

            self.message_user(request, "Tout s'est bien passé.")
            return HttpResponseRedirect(
                reverse(
                    "otpadmin:aidants_connect_web_cartetotp_change",
                    kwargs={"object_id": object_id},
                )
            )
        except Exception:
            logger.exception(
                "An error occured while trying to dissociate an aidant"
                "from their carte TOTP"
            )

            self.message_user(
                request,
                "Quelque chose s’est mal passé durant l'opération.",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
        )


# Display the following tables in the admin
admin_site.register(Organisation, OrganisationAdmin)
admin_site.register(Aidant, AidantAdmin)
admin_site.register(HabilitationRequest, HabilitationRequestAdmin)
admin_site.register(Usager, UsagerAdmin)
admin_site.register(Mandat, MandatAdmin)
admin_site.register(Journal, JournalAdmin)
admin_site.register(Connection, ConnectionAdmin)

admin_site.register(StaticDevice, StaticDeviceStaffAdmin)
admin_site.register(TOTPDevice, TOTPDeviceStaffAdmin)
admin_site.register(CarteTOTP, CarteTOTPAdmin)
