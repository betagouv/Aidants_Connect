import operator
from functools import reduce

from django.contrib import admin
from django.contrib.admin import ModelAdmin, SimpleListFilter, register
from django.contrib.admin.utils import quote
from django.db.models import Count, F, Q, QuerySet
from django.forms import CharField, Media
from django.urls import reverse
from django.utils.safestring import mark_safe

from import_export.admin import ImportMixin
from import_export.fields import Field
from import_export.forms import ImportForm
from import_export.resources import ModelResource
from import_export.widgets import BooleanWidget, ForeignKeyWidget

from aidants_connect.admin import VisibleToAdminMetier, admin_site
from aidants_connect_common.forms import WidgetAttrMixin
from aidants_connect_common.models import (
    Commune,
    Department,
    Formation,
    FormationAttendant,
    FormationOrganization,
    FormationType,
    Region,
)
from aidants_connect_common.widgets import JSModulePath


class CommuneImportForm(ImportForm, WidgetAttrMixin):
    commune_zrr_classification = CharField(
        label=(
            "Valeur indiquant qu'une commune est classé ZRR dans le fichier des zonages"
        ),
        initial="C - Classée en ZRR",
    )

    def __init__(self, import_formats, *args, **kwargs):
        super().__init__(import_formats, *args, **kwargs)
        self.widget_attrs(
            "resource",
            {"data-action": "commune-import-form#onOptionSelected"},
        )
        pass

    def clean(self):
        cleaned_data = super().clean()
        try:
            idx = next(
                idx
                for idx, name in self.fields["resource"].choices
                if name == ZRRResource.get_display_name()
            )
            if str(cleaned_data["resource"]) != str(idx):
                cleaned_data["commune_zrr_classification"] = None
        except StopIteration:
            cleaned_data["commune_zrr_classification"] = None

        return cleaned_data

    @property
    def media(self):
        return super().media + Media(js=[JSModulePath("js/communes-import-form.mjs")])


class CommuneResource(ModelResource):
    """
    Documentation for the imported CSV file is available at
    https://www.insee.fr/fr/information/6800685
    """

    insee_code = Field(attribute="insee_code", column_name="COM")
    name = Field(attribute="name", column_name="LIBELLE")
    department = Field(
        attribute="department",
        column_name="DEP",
        widget=ForeignKeyWidget(Department, field="insee_code"),
    )

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if row["TYPECOM"] != "COM":
            # Only import communes not communes associées or communes délégues
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    @classmethod
    def get_display_name(cls):
        return "Communes"

    class Meta:
        model = Commune
        fields = ("insee_code", "name", "department")
        import_id_fields = ("insee_code",)
        # There are 37_000+ communes which would take too much time to import
        # if not using bulk import.
        use_bulk = True
        skip_unchanged = True


class ZRRBooleanWidget(BooleanWidget):
    def __init__(self) -> None:
        self.commune_zrr_classification = None
        super().__init__()

    def clean(self, value, row=None, **kwargs):
        if self.commune_zrr_classification is None:
            return None
        return value == self.commune_zrr_classification


class ZRRResource(ModelResource):
    insee_code = Field(attribute="insee_code", column_name="CODGEO")
    zrr = Field(attribute="zrr", column_name="ZRR_SIMP", widget=ZRRBooleanWidget())

    def __init__(self, commune_zrr_classification, **kwargs):
        super().__init__(**kwargs)
        self.fields["zrr"].widget.commune_zrr_classification = (
            commune_zrr_classification
        )

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not original.insee_code:
            # Prevent creating instances from ZRR file
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    @classmethod
    def get_display_name(cls):
        return "Zones de Revitalisation Rurale"

    class Meta:
        model = Commune
        fields = ("insee_code", "zrr")
        import_id_fields = ("insee_code",)
        # There are 37_000+ communes which would take too much time to import
        # if not using bulk import.
        use_bulk = True
        skip_unchanged = True


@register(Commune, site=admin_site)
class OrganisationAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
    list_display = ("insee_code", "name", "department", "zrr")
    readonly_fields = ("insee_code", "name", "zrr")
    raw_id_fields = ("department",)
    search_fields = ("insee_code", "name", "department__name")
    resource_classes = [CommuneResource, ZRRResource]
    import_template_name = "admin/import_export/communes_import.html"
    import_form_class = CommuneImportForm

    def get_import_context_data(self, **kwargs):
        return {
            **super().get_import_context_data(**kwargs),
            "communes_resource_name": CommuneResource.get_display_name(),
            "zrr_resource_name": ZRRResource.get_display_name(),
        }

    def get_resource_kwargs(self, request, form: CommuneImportForm, **kwargs):
        return {
            **super().get_resource_kwargs(request, **kwargs),
            "commune_zrr_classification": getattr(form, "cleaned_data", {}).get(
                "commune_zrr_classification", None
            ),
        }


admin_site.register(Region)
admin_site.register(Department)


class RegionFilter(SimpleListFilter):
    template = "admin/filter-select.html"
    title = "Région"

    parameter_name = "region"
    filter_parameter_name = "zipcode"

    def lookups(self, request, model_admin):
        return [(r.insee_code, r.name) for r in Region.objects.all()] + [
            ("other", "Autre")
        ]

    def queryset(self, request, queryset):
        region_pk = self.value()

        if not region_pk:
            return

        if region_pk == "other":
            return queryset.filter(**{self.filter_parameter_name: 0})

        region = Region.objects.get(pk=region_pk)
        qgroup = reduce(
            operator.or_,
            (
                Q(
                    **{
                        f"{self.filter_parameter_name}__startswith": d.zipcode  # noqa: E501
                    }
                )
                for d in Department.objects.filter(region=region).all()
            ),
        )
        return queryset.filter(qgroup)


class DepartmentFilter(SimpleListFilter):
    template = "admin/filter-select.html"
    title = "Département"

    parameter_name = "department"
    filter_parameter_name = "zipcode"

    @classmethod
    def generate_filter_list(cls, region=None):
        if not region:
            return [
                (d.insee_code, f"{d.name} ({d.zipcode})")
                for d in Department.objects.all().order_by("name")
            ] + [("other", "Autre")]
        return [
            (
                dept.insee_code,
                f"{dept.name} ({dept.zipcode})",
            )
            for dept in Department.objects.filter(region=region).order_by("name")
        ]

    def lookups(self, request, model_admin):
        region = None
        region_pk = request.GET.get("region", "other")
        if region_pk != "other":
            region = Region.objects.get(pk=region_pk)
        return self.generate_filter_list(region=region)

    def queryset(self, request, queryset):
        department_value = self.value()
        if not department_value:
            return
        if department_value == "other":
            return queryset.filter(
                Q(**{f"{self.filter_parameter_name}__isnull_or_blank": True})
                | Q(**{f"{self.filter_parameter_name}__length__lt": 5})
            )
        return queryset.filter(
            **{f"{self.filter_parameter_name}__startswith": department_value}
        )


@register(FormationType, site=admin_site)
class FormationTypeAdmin(VisibleToAdminMetier, ModelAdmin):
    pass


class FormationFillingFilter(SimpleListFilter):
    title = "Remplissage de la formation"

    parameter_name = "formation_filling"

    def lookups(self, request, model_admin):
        return ("empty", "Vide"), ("not_empty", "Avec inscrits"), ("full", "Pleine")

    def queryset(self, request, queryset: QuerySet[Formation]):
        match self.value():
            case "empty":
                return queryset.annotate(attendants_count=Count("attendants")).filter(
                    attendants_count=0
                )
            case "not_empty":
                return queryset.annotate(attendants_count=Count("attendants")).filter(
                    attendants_count__gt=0, attendants_count__lt=F("max_attendants")
                )
            case "full":
                return queryset.annotate(attendants_count=Count("attendants")).filter(
                    attendants_count=F("max_attendants")
                )
            case _:
                return queryset


@register(Formation, site=admin_site)
class FormationAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "__str__",
        "start_datetime",
        "end_datetime",
        "number_of_attendants",
        "max_attendants",
        "status",
        "place",
        "id_grist",
        "type",
        "organisation",
    )
    raw_id_fields = ("type",)
    search_fields = ("id", "place", "id_grist")
    list_filter = (FormationFillingFilter, "status", "type", "organisation")
    readonly_fields = ("registered",)

    @admin.display(description="Nombre d'inscrits")
    def number_of_attendants(self, obj):
        return obj.number_of_attendants

    @admin.display(description="Personnes inscrites")
    def registered(self, obj: Formation):
        if not FormationAttendant.objects.filter(formation=obj).exists():
            return "Aucune personne inscrite"

        obj_url = "%s?q=%s" % (
            reverse(
                "admin:%s_%s_changelist"
                % (
                    FormationAttendant._meta.app_label,
                    FormationAttendant._meta.model_name,
                ),
                current_app=self.admin_site.name,
            ),
            obj.type.label,
        )
        return mark_safe(
            f'<a href={obj_url} target="_blank" rel="noopener noreferrer">Voir la liste des personnes inscrites</a>'  # noqa: E501
        )


class FormationAttendantSyncInGrist(SimpleListFilter):
    title = "Synchro dans Grist"

    parameter_name = "attendant_in_grist"

    def lookups(self, request, model_admin):
        return (
            ("in_grist", "Synchro dans Grist"),
            ("not_in_grist", "Pas Synchro dans Grist"),
        )

    def queryset(self, request, queryset: QuerySet[FormationAttendant]):
        match self.value():
            case "in_grist":
                return queryset.exclude(id_grist="")
            case "not_in_grist":
                return queryset.filter(id_grist="")
            case _:
                return queryset


@register(FormationAttendant, site=admin_site)
class FormationAttendantAdmin(VisibleToAdminMetier, ModelAdmin):
    fields = (
        "created_at",
        "attendant",
        "registered",
        "formation",
        "state",
        "id_grist",
        "get_formation_id_grist",
    )
    raw_id_fields = ("attendant", "formation")
    readonly_fields = [
        "created_at",
        "get_formation_id_grist",
        "id_grist",
        "state",
        "registered",
    ]
    readonly_fields_for_edit = [
        "created_at",
        "get_formation_id_grist",
        "registered",
        "formation",
        "attendant",
        "state",
        "id_grist",
    ]
    list_display = (
        "formation",
        "id_grist",
        "get_formation_type_label",
        "attendant",
        "state",
        "created_at",
        "updated_at",
        "get_formation_id_grist",
    )
    search_fields = (
        "formation__type__label",
        "formation__pk",
        "formation__id_grist",
        "attendant__email",
    )
    list_filter = ["state", "formation__type", FormationAttendantSyncInGrist]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields_for_edit
        else:
            return self.readonly_fields

    @admin.display(description="Formation Type", ordering="formation__type__label")
    def get_formation_type_label(self, obj):
        return obj.formation.type.label

    @admin.display(description="Formation Id Grist", ordering="formation__id_grist")
    def get_formation_id_grist(self, obj):
        return obj.formation.id_grist

    @admin.display(description="Personne inscrite")
    def registered(self, obj: FormationAttendant):
        obj_url = reverse(
            "otpadmin:aidants_connect_web_habilitationrequest_change",
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        return mark_safe(f'<a href="{obj_url}">{obj.attendant.get_full_name()}</a>')


@register(FormationOrganization, site=admin_site)
class FormationOrganizationAdmin(VisibleToAdminMetier, ModelAdmin):
    fields = ("name", "contacts", "private_contacts")
    list_display = ("name", "contacts", "private_contacts")
    search_fields = ("name", "contacts", "private_contacts")
