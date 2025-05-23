import logging

from django.conf import settings
from django.contrib import admin
from django.contrib import messages as django_messages
from django.contrib.admin import ModelAdmin, register
from django.db.models import QuerySet
from django.http import Http404, HttpResponse
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from celery.result import AsyncResult
from celery.states import FAILURE, SUCCESS
from rest_framework.authtoken.admin import TokenAdmin

from aidants_connect.admin import VisibleToAdminMetier, admin_site
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import CoReferentNonAidantRequest, ExportRequest

from ..tasks import email_co_rerefent_creation

logger = logging.getLogger()


TokenAdmin.raw_id_fields = ["user"]


class ConnectionAdmin(ModelAdmin):
    list_display = ("id", "usager", "aidant", "complete")
    raw_id_fields = ("usager", "aidant", "organisation")
    readonly_fields = ("autorisation",)
    search_fields = (
        "id",
        "aidant__first_name",
        "aidant__last_name",
        "aidant__email",
        "usager__family_name",
        "usager__given_name",
        "usager__email",
        "consent_request_id",
        "organisation__name",
    )


@register(ExportRequest, site=admin_site)
class ExportRequestAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = fields = readonly_fields = ("aidant", "date", "state", "file_link")

    def file_link(self, obj: ExportRequest):
        if obj.is_ongoing:
            return "L'export est en cours…"
        if not obj.file_path.exists() and AsyncResult(str(obj.task_uuid)).state not in [
            SUCCESS,
            FAILURE,
        ]:
            return "Le fichier n'existe plus"
        route = reverse(
            "otpadmin:aidants_connect_web_export_request_download",
            kwargs={"request_id": obj.pk},
        )
        if obj.is_error:
            return mark_safe(
                f"""<a href="{route}">Une erreur s'est produite (voir)</a>"""
            )
        elif obj.is_done:
            return mark_safe(f"""<a href="{route}">Télécharger lʼexport</a>""")
        else:
            return "Lʼexport est en cours"

    file_link.short_description = "Lien du fichier"

    def add_view(self, request, form_url="", extra_context=None):
        try:
            new_object = ExportRequest.objects.get(
                aidant=request.user, state=ExportRequest.ExportRequestState.ONGOING
            )
            django_messages.warning(request, "Un export est déjà en cours")
            return self._response_post_save(request, new_object)
        except ExportRequest.DoesNotExist:
            new_object = ExportRequest.objects.create(aidant=request.user)
            django_messages.success(request, "Un export a été lancé")
            self.log_addition(
                request, new_object, f"Un export a été lancé par {new_object.aidant}"
            )
            return self.response_add(request, new_object)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.is_staff:
            return qs.filter(aidant=request.user)
        else:
            return qs.none()

    def get_urls(self):
        return [
            path(
                "download/<int:request_id>",
                self.admin_site.admin_view(self.download),
                name="aidants_connect_web_export_request_download",
            ),
            *super().get_urls(),
        ]

    def download(self, request, request_id):
        try:
            export_request = ExportRequest.objects.get(
                pk=request_id, aidant=request.user
            )
        except ExportRequest.DoesNotExist:
            raise Http404

        if export_request.is_ongoing:
            raise Http404

        if export_request.file_path.exists():
            with open(export_request.file_path, "rb") as csv:
                return HttpResponse(
                    csv,
                    content_type="text/csv",
                    headers={
                        "Content-Disposition": f'attachment; filename="{export_request.file_path.name}"'  # noqa: E501
                    },
                )

        result = AsyncResult(str(export_request.task_uuid))
        if result.state in [SUCCESS, FAILURE]:
            with open(export_request.file_path, "w") as f:
                result = str(result.get())
                f.write(result)

                return HttpResponse(
                    result.encode(),
                    content_type="text/csv",
                    headers={
                        "Content-Disposition": f'attachment; filename="{export_request.file_path.name}"'  # noqa: E501
                    },
                )
        else:
            raise Http404


@register(CoReferentNonAidantRequest, site=admin_site)
class CoReferentNonAidantRequestAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "profession",
        "email",
        "get_status_display",
    )
    raw_id_fields = ("organisation",)
    readonly_fields = ("created_at", "updated_at")
    search_fields = (
        "id",
        "first_name",
        "last_name",
        "profession",
        "email",
        "organisation",
        "organisation__name",
    )

    list_filter = ("status",)

    actions = ("mark_validated", "mark_refused")

    @admin.display(description="Status de la demande")
    def get_status_display(self, obj):
        return obj.get_status_display()

    @admin.action(description="Créer les comptes co-référents sélectionnés")
    def mark_validated(self, request, queryset: QuerySet[CoReferentNonAidantRequest]):
        instances = [
            instance.pk
            for x in queryset
            if (instance := x.create_referent_non_aidant())
        ]

        self.message_user(
            request, f"{len(instances)} référents non-aidants ont été créés"
        )

        if settings.FF_EMAIL_CO_RERERENT_CREATION:
            email_co_rerefent_creation.delay(instances)

    @admin.action(
        description="Refuser la création les comptes co-référents sélectionnés"
    )
    def mark_refused(self, request, queryset: QuerySet[CoReferentNonAidantRequest]):
        queryset.update(status=ReferentRequestStatuses.STATUS_REFUSED)
        self.message_user(
            request,
            f"{queryset.count()} profils de référents non-aidants ont été refusés.",
        )
