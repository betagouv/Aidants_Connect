import logging

from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.urls import reverse
from django.utils.safestring import mark_safe

from import_export import resources
from import_export.admin import ExportActionModelAdmin, ImportMixin
from import_export.fields import Field
from import_export.results import RowResult

from aidants_connect.admin import VisibleToAdminMetier
from aidants_connect_common.admin import DepartmentFilter, RegionFilter
from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation

from .utils import SpecificDeleteActionsMixin

logger = logging.getLogger()


class ExportHabilitationRequestAndAidantAndOrganisationResource(
    resources.ModelResource
):
    def dehydrate_responsable_de_data_pass_id(self, habilitation_or_aidant):
        if habilitation_or_aidant.__class__ == HabilitationRequest:
            return ""
        q_orgas = habilitation_or_aidant.responsable_de
        str_list_data_pass_id = ""
        for one_orga in q_orgas.all():
            if one_orga.data_pass_id:
                str_list_data_pass_id += f"{one_orga.data_pass_id}|"
        return str_list_data_pass_id

    id = Field(attribute="id", column_name="ID")
    first_name = Field(attribute="first_name", column_name="Prénom")
    last_name = Field(attribute="last_name", column_name="Nom")
    email = Field(attribute="email", column_name="email")
    organisation__data_pass_id = Field(
        attribute="organisation__data_pass_id", column_name="data_pass_id"
    )
    organisation__name = Field(
        attribute="organisation__name", column_name="Nom Organisation"
    )
    organisation__siret = Field(attribute="organisation__siret", column_name="siret")
    organisation__address = Field(
        attribute="organisation__address", column_name="address"
    )
    organisation__city = Field(attribute="organisation__city", column_name="ville")
    organisation__zipcode = Field(
        attribute="organisation__zipcode", column_name="Code postal"
    )
    organisation__type__id = Field(
        attribute="organisation__type__id", column_name="Type ID"
    )
    organisation__type__name = Field(
        attribute="organisation__type__name", column_name="Nom Type"
    )
    responsable_de_data_pass_id = Field(column_name="Data pass Id Orga Responsable")

    class Meta:
        """We need a resources.ModelResource, so we define Aidant.
        But we will use this resource for Aidant and HabilitationRequest.
        We can do that because the fields we want to export are the same
        and have the same names for both models
        """

        model = Aidant
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "organisation__data_pass_id",
            "organisation__name",
            "organisation__siret",
            "organisation__address",
            "organisation__city",
            "organisation__zipcode",
            "organisation__type__id",
            "organisation__type__name",
            "responsable_de_data_pass_id",
        )


class OrganisationResource(resources.ModelResource):
    datapass_id = Field(attribute="data_pass_id", column_name="Numéro de demande")
    name = Field(attribute="name", column_name="Nom de la structure")
    zipcode = Field(attribute="zipcode", column_name="Code postal de la structure")
    city = Field(attribute="city", column_name="Ville de la structure")
    siret = Field(attribute="siret", column_name="SIRET de l’organisation")
    status_not_field = Field(
        column_name="Statut de la demande (send = à valider; pending = brouillon)"
    )

    def import_field(self, field, obj, data, is_m2m=False, **kwargs):
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
            super().import_field(field, obj, data, is_m2m, **kwargs)

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

    def skip_row(self, instance, original, row, import_validation_errors=None):
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


class OrganisationAdmin(
    SpecificDeleteActionsMixin,
    ImportMixin,
    ExportActionModelAdmin,
    VisibleToAdminMetier,
    ModelAdmin,
):
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
        "france_services_label",
    )
    readonly_fields = (
        "display_responsables",
        "display_aidants",
        "display_habilitation_requests",
    )
    search_fields = ("id", "name", "siret", "data_pass_id")
    list_filter = (
        RegionFilter,
        DepartmentFilter,
        "is_active",
        "france_services_label",
        "type",
        WithoutDatapassIdFilter,
        "is_experiment",
    )

    # For bulk import
    resource_classes = [OrganisationResource]
    import_export_change_list_template = (
        "aidants_connect_web/admin/import_export/change_list_organisation_import.html"
    )
    import_template_name = (
        "aidants_connect_web/admin/import_export/import_organisation.html"
    )

    actions = (
        "find_zipcode_in_address",
        "deactivate_organisations",
        "activate_organisations",
        "specific_delete_action",
    )

    def get_export_resource_classes(self):
        return [ExportHabilitationRequestAndAidantAndOrganisationResource]

    @classmethod
    def get_list_for_export_sandbox(cls, queryset):
        aidants = list(Aidant.objects.filter(organisation__in=queryset))
        habilitations = list(
            HabilitationRequest.objects.filter(organisation__in=queryset)
        )
        export_list = aidants + habilitations
        return export_list

    def get_data_for_export(self, request, queryset, *args, **kwargs):
        export_list = self.get_list_for_export_sandbox(queryset)
        export_form = kwargs.pop("export_form", None)
        return self.choose_export_resource_class(export_form)(
            **self.get_export_resource_kwargs(request, *args, **kwargs)
        ).export(*args, queryset=export_list, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.data_pass_id:
            readonly_fields.append("data_pass_id")
        return readonly_fields

    def display_responsables(self, obj):
        return self.format_list_of_aidants(obj.responsables.order_by("last_name").all())

    display_responsables.short_description = "Référents"

    def display_aidants(self, obj):
        return self.format_list_of_aidants(obj.aidants.order_by("last_name").all())

    display_aidants.short_description = "Aidants"

    def format_list_of_aidants(self, aidants_list):
        return mark_safe(
            "<table><tr>"
            + '<th scope="col">id</th><th scope="col">Nom</th><th>E-mail</th><th>Carte TOTP</th></tr><tr>'  # noqa
            + "</tr><tr>".join(
                '<td>{}</td><td><a href="{}">{}</a></td><td>{}</td><td>{}</td>'.format(
                    aidant.id,
                    reverse(
                        "otpadmin:aidants_connect_web_aidant_change",
                        kwargs={"object_id": aidant.id},
                    ),
                    aidant,
                    aidant.email,
                    aidant.number_totp_card,
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

    def specific_delete_action(self, request, queryset):
        self._specific_delete_action(request, queryset)

    specific_delete_action.short_description = (
        "Supprimer les organisations sélectionnées"
    )
