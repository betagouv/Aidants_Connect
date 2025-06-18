from django.contrib import admin
from django.contrib.admin import ModelAdmin, register
from django.utils.safestring import mark_safe

from aidants_connect.admin import (
    VisibleToOFUser,
    VisibleToOFUserEditOnly,
    VisibleToOFUserReadOnly,
    admin_of_site,
)
from aidants_connect_common.models import (
    Formation,
    FormationAttendant,
    FormationOrganization,
    FormationType,
)

from .admin_ac import (
    FormationAdmin,
    FormationAttendantAdmin,
    FormationContactPrivateInlineAdmin,
    FormationContactPublicInlineAdmin,
    HalfDayClassInlineAdmin,
)
from .filter import FormationFillingFilter


@register(FormationAttendant, site=admin_of_site)
class FormationAttendantOFAdmin(VisibleToOFUserEditOnly, FormationAttendantAdmin):
    list_filter = [
        "state",
        "formation__type",
        "attendant__formation_done",
        "attendant__test_pix_passed",
        "formation__intra",
    ]
    list_display = (
        # "id_grist",
        "attendant",
        "formation",
        "state",
        "formation_participation",
        "get_pix_result",
        "created_at",
        "updated_at",
        "get_formation_id",
        "get_formation_id_grist",
    )
    readonly_fields = [
        "created_at",
        "get_formation_id_grist",
        "id_grist",
        "state",
        "registered",
        "attendant_structure",
        "formation_participation",
        "get_formation_id",
        "display_responsables",
        "get_pix_result",
    ]
    readonly_fields_for_edit = [
        "created_at",
        "get_formation_id_grist",
        "attendant_structure",
        "registered",
        "formation",
        "attendant",
        "get_pix_result",
        "state",
        "id_grist",
        "formation_participation",
        "get_formation_id",
        "display_responsables",
    ]
    fields = None

    fieldsets = (
        (
            "Informations Apprenant",
            {
                "fields": (
                    "registered",
                    "attendant_structure",
                    "display_responsables",
                )
            },
        ),
        (
            "Formation et Inscription",
            {
                "fields": (
                    "formation",
                    "state",
                    "formation_participation",
                    "get_pix_result",
                )
            },
        ),
        (
            "Informations Technique",
            {
                "fields": (
                    "created_at",
                    "id_grist",
                    "get_formation_id_grist",
                    "get_formation_id",
                )
            },
        ),
    )

    @admin.display(description="Personne inscrite")
    def registered(self, obj: FormationAttendant):

        return mark_safe(
            f'<ul> <li>Prénom : {obj.attendant.first_name} </li><li>Nom : {obj.attendant.last_name} </li><li>Email: <a href="mailto:{obj.attendant.email}">{obj.attendant.email}</a></li></ul> '  # noqa
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        one_fattendant = self.get_object(request, object_id)
        extra_context = {
            "view_action_button": True if one_fattendant.state == 1 else False
        }
        return self.changeform_view(request, object_id, form_url, extra_context)

    def display_responsables(self, obj):
        return self.format_list_of_aidants(
            obj.attendant.organisation.responsables.order_by("last_name").all()
        )

    display_responsables.short_description = "Référents"

    def format_list_of_aidants(self, aidants_list):
        return mark_safe(
            "<table><tr>"
            + '<th scope="col">Nom</th><th>E-mail</th><th>Téléphone</th><tr>'  # noqa
            + "</tr><tr>".join(
                "<td>{}</td><td>{}</td><td>{}".format(  # noqa
                    aidant, aidant.email, aidant.phone
                )
                for aidant in aidants_list
            )
            + "</tr></table>"
        )


@register(FormationType, site=admin_of_site)
class FormationTypeOFAdmin(VisibleToOFUserReadOnly, ModelAdmin):
    show_change_link = False


class FormationAttendantOFInlineAdmin(VisibleToOFUserReadOnly, admin.TabularInline):
    model = FormationAttendant
    show_change_link = True
    can_delete = False

    extra = 0
    fields = (
        "last_name",
        "first_name",
        "structure",
        "email",
        "state",
    )

    def last_name(self, obj):
        return obj.attendant.last_name

    last_name.short_description = "Nom"

    def first_name(self, obj):
        return obj.attendant.first_name

    first_name.short_description = "Prénom"

    def structure(self, obj):
        return obj.attendant.organisation

    structure.short_description = "Structure"

    def email(self, obj):
        return obj.attendant.email

    email.short_description = "Email"

    readonly_fields = (
        "state",
        "attendant",
        "last_name",
        "first_name",
        "structure",
        "email",
    )
    raw_id_fields = ("attendant",)


@register(Formation, site=admin_of_site)
class FormationOFAdmin(VisibleToOFUser, FormationAdmin):
    inlines = (
        HalfDayClassInlineAdmin,
        FormationAttendantOFInlineAdmin,
    )

    list_filter = (
        FormationFillingFilter,
        "publish_or_not",
        "status",
        "duration",
        "intra",
    )
    readonly_fields = ("id_grist", "id", "type")
    readonly_fields_for_edit = ("id_grist", "id", "type", "organisation")

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields["organisation"].queryset = (
            FormationOrganization.objects.filter(users_of=request.user)
        )
        return form

    def save_form(self, request, form, change):
        instance = super().save_form(request, form, change)
        instance.type = instance.organisation.type
        return instance

    def get_queryset(self, request):
        # For Django < 1.6, override queryset instead of get_queryset
        qs = super(FormationAdmin, self).get_queryset(request)
        if request.user.is_of_user:
            return qs.filter(
                organisation__in=request.user.organizations_formations.all()
            )
        return qs


@register(FormationOrganization, site=admin_of_site)
class FormationOrganizationOFAdmin(VisibleToOFUserEditOnly, ModelAdmin):
    # fields = ("name", "contacts", "private_contacts", "type", "region")
    list_display = ("name", "type", "region")
    search_fields = ("name", "contacts", "private_contacts", "region")
    readonly_fields = ("users_of", "contacts", "private_contacts")
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        return qs.filter(users_of=user)
