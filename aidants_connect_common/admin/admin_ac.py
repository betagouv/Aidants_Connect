from django.contrib import admin
from django.contrib.admin import ModelAdmin, SimpleListFilter, register
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from import_export.admin import ExportMixin, ImportMixin

from aidants_connect.admin import (
    VisibleToAdminMetier,
    VisibleToOFUser,
    admin_of_site,
    admin_site,
)
from aidants_connect_common.forms import (
    AdminChangeFormationForm,
    AdminValidateorDisableForm,
)
from aidants_connect_common.models import (
    Commune,
    Department,
    Formation,
    FormationAttendant,
    FormationContactPrivate,
    FormationContactPublic,
    FormationOrganization,
    FormationType,
    HalfDayClass,
    Region,
)

from .filter import FormationFillingFilter, FormationRegionFilter
from .forms import CommuneImportForm, ReportFormationForm
from .resources import (
    CommuneResource,
    FormationAttendantResource,
    FormationResource,
    ZRRResource,
)


@register(Commune, site=admin_site)
class CommuneAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
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


@register(FormationType, site=admin_site)
class FormationTypeAdmin(VisibleToAdminMetier, ModelAdmin):
    pass


class FormationAttendantInlineAdmin(VisibleToAdminMetier, admin.TabularInline):
    model = FormationAttendant
    show_change_link = True
    can_delete = False
    extra = 0
    fields = (
        "attendant",
        "state",
    )
    readonly_fields = ("state",)
    raw_id_fields = ("attendant",)


class FormationContactPublicInlineAdmin(VisibleToOFUser, admin.TabularInline):
    model = FormationContactPublic
    show_change_link = True
    extra = 0
    fields = ("first_name", "last_name", "email")


class FormationContactPrivateInlineAdmin(VisibleToOFUser, admin.TabularInline):
    model = FormationContactPrivate
    show_change_link = True
    extra = 0
    fields = ("first_name", "last_name", "email")


class HalfDayClassInlineAdmin(VisibleToOFUser, admin.TabularInline):
    model = HalfDayClass
    show_change_link = True
    extra = 0
    fields = ("start_datetime", "end_time", "formation")


@register(Formation, site=admin_site)
# @register(Formation, site=admin_of_site)
class FormationAdmin(ExportMixin, VisibleToAdminMetier, ModelAdmin):
    resource_classes = [
        FormationResource,
    ]
    list_display = (
        "__str__",
        "id_grist",
        "id",
        "start_datetime",
        "end_datetime",
        "number_of_attendants",
        "max_attendants",
        "status",
        "place",
        "id_grist",
        "type",
        "organisation",
        "intra",
    )
    raw_id_fields = ("type",)
    search_fields = ("id", "place", "id_grist")

    fieldsets = (
        (
            "Informations Formation",
            {
                "fields": (
                    "organisation",
                    "start_datetime",
                    "end_datetime",
                    "duration",
                    "status",
                    "max_attendants",
                    "place",
                    "type",
                    "intra",
                )
            },
        ),
        (
            "Informations publications",
            {
                "fields": (
                    "state",
                    "publish_or_not",
                )
            },
        ),
        (
            "Informations Autre",
            {
                "fields": (
                    "description",
                    "id",
                    "id_grist",
                )
            },
        ),
    )

    list_filter = (
        FormationFillingFilter,
        "publish_or_not",
        "status",
        "duration",
        "type",
        "intra",
        FormationRegionFilter,
        "organisation",
    )
    readonly_fields = ("id_grist", "id")
    actions = ["publish_formation", "unpublish_formation"]
    inlines = (
        HalfDayClassInlineAdmin,
        FormationAttendantInlineAdmin,
    )

    change_form_template = "aidants_connect_common/admin/formation/change_form.html"

    def get_urls(self):
        return [
            path(
                "<path:object_id>/report_formation/",
                # self.admin_site.admin_view(self.report_one_formation),
                admin_of_site.admin_view(self.report_one_formation),
                name="aidants_connect_common_report_formation",
            ),
            # path(
            #     "<path:object_id>/export_apprenant_formation/",
            #     # self.admin_site.admin_view(self.report_one_formation),
            #     admin_of_site.admin_view(self.export_apprenant_formation),
            #     name="aidants_connect_common_export_apprenant_formation",
            # ),
            *super().get_urls(),
        ]

    def report_one_formation(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__report_one_formation_get(request, object_id)
        else:
            return self.__report_one_formation_post(request, object_id)

    def __report_one_formation_get(self, request, object_id):
        formation = Formation.objects.get(id=object_id)
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": formation,
            "form": ReportFormationForm(instance=formation),
        }

        return render(
            request,
            "aidants_connect_common/admin/formation/report_one_formation.html",  # noqa
            view_context,
        )

    def __report_one_formation_post(self, request, object_id):
        formation = Formation.objects.get(id=object_id)
        form = ReportFormationForm(instance=formation, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()
        form.save()
        redirect_path = reverse("adminof:aidants_connect_common_formation_changelist")
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        self.message_user(
            request,
            (f"La formation {object}  " f"a bien été modifiée."),
        )
        return HttpResponseRedirect(redirect_path)

    def publish_formation(self, request: HttpRequest, queryset: QuerySet):
        queryset.update(publish_or_not=True)
        self.message_user(request, f"{queryset.count()} formations ont été publiées")

    publish_formation.short_description = (
        "Rendre disponible à l'inscription les formations sélectionnéss"
    )

    def unpublish_formation(self, request: HttpRequest, queryset: QuerySet):
        queryset.update(publish_or_not=False)
        self.message_user(
            request,
            f"{queryset.count()} formations ne sont plus disponibles à l'inscription",
        )

    unpublish_formation.short_description = (
        "Rendre indisponible à l'inscription les formations sélectionnéss"
    )

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
# @register(FormationAttendant, site=admin_of_site)
class FormationAttendantAdmin(VisibleToAdminMetier, ExportMixin, ModelAdmin):
    resource_classes = [
        FormationAttendantResource,
    ]
    list_filter = [
        "state",
        "formation__type",
        "attendant__formation_done",
        "attendant__test_pix_passed",
        "formation__intra",
        FormationAttendantSyncInGrist,
    ]

    fields = (
        "created_at",
        "attendant",
        "attendant_structure",
        "registered",
        "formation",
        "state",
        "formation_participation",
        "get_pix_result",
        "id_grist",
        "get_formation_id_grist",
    )
    raw_id_fields = ("attendant", "formation")
    readonly_fields = [
        "created_at",
        "get_formation_id_grist",
        "id_grist",
        # "state",
        "registered",
        "attendant_structure",
        "formation_participation",
        "get_formation_id",
        "get_pix_result",
    ]
    readonly_fields_for_edit = [
        "created_at",
        "get_formation_id_grist",
        "attendant_structure",
        "registered",
        "formation",
        "attendant",
        # "state",
        "id_grist",
        "formation_participation",
        "get_formation_id",
        "get_pix_result",
    ]
    list_display = (
        "attendant",
        "id_grist",
        "formation",
        "formation_participation",
        "get_pix_result",
        "state",
        "get_formation_type_label",
        "created_at",
        "updated_at",
        "get_formation_id",
        "get_formation_id_grist",
    )
    search_fields = (
        "formation__type__label",
        "formation__pk",
        "formation__id_grist",
        "attendant__email",
    )

    actions = ["validate_inscription", "disable_inscription"]
    change_form_template = (
        "aidants_connect_common/admin/formation_attendant/change_form.html"
    )

    @admin.display(description="Résultat PIX")
    def get_pix_result(self, obj):
        return obj.get_pix_result()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {"view_action_button": True}
        return self.changeform_view(request, object_id, form_url, extra_context)

    def get_queryset(self, request):
        # For Django < 1.6, override queryset instead of get_queryset
        qs = super(FormationAttendantAdmin, self).get_queryset(request)
        if request.user.is_of_user:
            return qs.filter(
                formation__organisation__in=request.user.organizations_formations.all()
            )
        return qs

    def disable_inscription(self, request: HttpRequest, queryset: QuerySet):
        from aidants_connect_common.constants import FormationAttendantState

        queryset.update(state=FormationAttendantState.DEFAULT)
        self.message_user(request, f"{queryset.count()} inscriptions ont été annulées")

    disable_inscription.short_description = "Annuler les inscriptions sélectionnées"

    def validate_inscription(self, request: HttpRequest, queryset: QuerySet):
        for one_fattendant in queryset:
            one_fattendant.attendant.formation_done = True
            one_fattendant.attendant.date_formation = (
                one_fattendant.formation.start_datetime
            )
            # print(one_fattendant.attendant)
            one_fattendant.attendant.save()

        self.message_user(
            request,
            f"{queryset.count()} participations aux formations ont été validées",
        )

    validate_inscription.short_description = (
        "Valider la participation aux formations des inscriptions sélectionnées"
    )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/accept/",
                # self.admin_site.admin_view(self.validate_one_inscription),
                admin_of_site.admin_view(self.validate_one_inscription),
                name="aidants_connect_common_validate_inscription",
            ),
            path(
                "<path:object_id>/refuse/",
                # self.admin_site.admin_view(self.disable_one_inscription),
                admin_of_site.admin_view(self.disable_one_inscription),
                name="aidants_connect_common_disable_inscription",
            ),
            path(
                "<path:object_id>/change_date/",
                # self.admin_site.admin_view(self.change_one_inscription),
                admin_of_site.admin_view(self.change_one_inscription),
                name="aidants_connect_common_change_inscription",
            ),
            *super().get_urls(),
        ]

    def disable_one_inscription(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__disable_inscription_get(request, object_id)
        else:
            return self.__disable_inscription_post(request, object_id)

    def validate_one_inscription(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__validate_inscription_get(request, object_id)
        else:
            return self.__validate_inscription_post(request, object_id)

    def change_one_inscription(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__change_inscription_get(request, object_id)
        else:
            return self.__change_inscription_post(request, object_id)

    def __change_inscription_get(self, request: HttpRequest, object_id):
        one_fattendant = FormationAttendant.objects.get(id=object_id)

        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": one_fattendant,
            "subject": "Basculer l'inscription de l'apprenant sur une nouvelle formation",  # noqa
            "form": AdminChangeFormationForm(instance=one_fattendant),
        }

        return render(
            request,
            "aidants_connect_common/admin/formation_attendant/change_formation_form.html",  # noqa
            view_context,
        )

    def __change_inscription_post(self, request, object_id):
        object = FormationAttendant.objects.get(id=object_id)
        form = AdminChangeFormationForm(instance=object, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()
        form.save()
        redirect_path = reverse(
            "adminof:aidants_connect_common_formationattendant_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        self.message_user(
            request,
            (
                f"L'inscription en formation de {object.attendant}  "
                f"a bien été modifiée."
            ),
        )
        return HttpResponseRedirect(redirect_path)

    def __disable_inscription_get(self, request: HttpRequest, object_id):
        one_fattendant = FormationAttendant.objects.get(id=object_id)

        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": one_fattendant,
            "subject": "Annuler l'inscription de l'apprenant",
            "form": AdminValidateorDisableForm(one_fattendant),
        }

        return render(
            request,
            "aidants_connect_common/admin/formation_attendant/refusal_form.html",
            view_context,
        )

    def __disable_inscription_post(self, request, object_id):
        from aidants_connect_common.constants import FormationAttendantState

        object = FormationAttendant.objects.get(id=object_id)

        form = AdminValidateorDisableForm(object, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()
        object.state = FormationAttendantState.CANCELLED
        object.save()
        object.attendant.formation_done = False
        object.attendant.save()
        redirect_path = reverse(
            "adminof:aidants_connect_common_formationattendant_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        self.message_user(
            request,
            (
                f"L'inscription en formation de {object.attendant}  "
                f"a bien été annulé."
            ),
        )
        return HttpResponseRedirect(redirect_path)

    def __validate_inscription_get(self, request: HttpRequest, object_id):
        one_fattendant = FormationAttendant.objects.get(id=object_id)

        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": one_fattendant,
            "subject": "Valider la présence de l'apprenant",
            "form": AdminValidateorDisableForm(one_fattendant),
        }

        return render(
            request,
            "aidants_connect_common/admin/formation_attendant/accept_form.html",
            view_context,
        )

    def __validate_inscription_post(self, request, object_id):
        object = FormationAttendant.objects.get(id=object_id)
        form = AdminValidateorDisableForm(object, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()
        object.attendant.formation_done = True
        object.attendant.date_formation = object.formation.start_datetime
        object.attendant.save()
        redirect_path = reverse(
            "adminof:aidants_connect_common_formationattendant_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        self.message_user(
            request,
            (
                f"Tout s'est bien passé. La présence en formation de {object.attendant}  "  # noqa
                f"a bien été validée."
            ),
        )
        return HttpResponseRedirect(redirect_path)

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

    @admin.display(description="Formation Id", ordering="formation__id")
    def get_formation_id(self, obj):
        return obj.formation.id

    @admin.display(description="Structure")
    def attendant_structure(self, obj: FormationAttendant):
        obj_url = reverse(
            "adminof:aidants_connect_web_organisation_change",
            args=(quote(obj.attendant.organisation.pk),),
            current_app=self.admin_site.name,
        )
        return mark_safe(f'<a href="{obj_url}">{obj.attendant.organisation}</a>')

    @admin.display(description="A Participé à la formation ? ")
    def formation_participation(self, obj):
        if obj.attendant.formation_done:
            return "Oui"
        return "Non ou Inconnu"

    @admin.display(description="Personne inscrite")
    def registered(self, obj: FormationAttendant):
        obj_url = reverse(
            "adminof:aidants_connect_web_habilitationrequest_change",
            args=(quote(obj.attendant.pk),),
            current_app=self.admin_site.name,
        )
        return mark_safe(
            f'<a href="{obj_url}">{obj.attendant.get_full_name()}</a> Email: <a href="mailto:{obj.attendant.email}">{obj.attendant.email}</a> '  # noqa
        )


@register(FormationOrganization, site=admin_site)
class FormationOrganizationAdmin(VisibleToAdminMetier, ModelAdmin):
    # fields = ("name", "contacts", "private_contacts", "type", "region")
    list_display = ("name", "type", "region")
    search_fields = ("name", "contacts", "private_contacts", "region")

    fieldsets = (
        (
            "Informations Organisation",
            {
                "fields": (
                    "name",
                    "type",
                    "region",
                )
            },
        ),
        ("Utilisateurs Django de l'OF", {"fields": ("users_of",)}),
        (
            "Ancienne versions des données",
            {
                "fields": (
                    "contacts",
                    "private_contacts",
                )
            },
        ),
    )
    inlines = (FormationContactPublicInlineAdmin, FormationContactPrivateInlineAdmin)
