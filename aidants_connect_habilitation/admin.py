from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin, StackedInline, TabularInline
from django.core.mail import send_mail
from django.http import HttpResponseNotAllowed
from django.shortcuts import render
from django.template import loader
from django.urls import path
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe

from django_reverse_admin import ReverseModelAdmin

from aidants_connect.admin import (
    DepartmentFilter,
    RegionFilter,
    VisibleToAdminMetier,
    admin_site,
)
from aidants_connect_habilitation.forms import AdminAcceptationForm
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    OrganisationRequest,
    RequestMessage,
)
from aidants_connect_web.models import Organisation


class OrganisationRequestInline(VisibleToAdminMetier, TabularInline):
    model = OrganisationRequest
    show_change_link = True
    fields = ("id", "status", "name", "type", "address", "zipcode", "city")
    readonly_fields = fields
    extra = 0
    can_delete = False


class IssuerAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "last_name",
        "first_name",
        "phone",
    )
    readonly_fields = ("issuer_id",)
    inlines = (OrganisationRequestInline,)


class AidantRequestInline(VisibleToAdminMetier, TabularInline):
    model = AidantRequest
    show_change_link = True
    extra = 0


class MessageInline(VisibleToAdminMetier, StackedInline):
    model = RequestMessage
    extra = 1


class OrganisationRequestAdmin(VisibleToAdminMetier, ReverseModelAdmin):
    list_filter = ("status", RegionFilter, DepartmentFilter)
    list_display = ("name", "issuer", "status", "data_pass_id")
    search_fields = ("data_pass_id", "name")
    raw_id_fields = ("issuer", "organisation")
    fields = (
        "issuer",
        "data_pass_id",
        "status",
        "organisation",
        "type",
        "type_other",
        "name",
        "siret",
        "address",
        "zipcode",
        "city",
        "is_private_org",
        "partner_administration",
        "france_services_label",
        "france_services_number",
        "web_site",
        "mission_description",
        "avg_nb_demarches",
        "cgu",
        "dpo",
        "without_elected",
        "professionals_only",
    )
    readonly_fields = (
        "public_service_delegation_attestation",
        "uuid",
        "organisation",
        "status",
        "data_pass_id",
        "mission_description",
        "avg_nb_demarches",
        "cgu",
        "dpo",
        "without_elected",
        "professionals_only",
    )
    inlines = (
        AidantRequestInline,
        MessageInline,
    )
    inline_type = "stacked"
    inline_reverse = ("manager",)

    actions = ("accept_selected_requests",)
    change_form_template = (
        "aidants_connect_habilitation/admin/organisation_request/change_form.html"
    )

    def accept_selected_requests(self, request, queryset):
        orgs_created = 0
        for organisation_request in queryset:
            try:
                if organisation_request.accept_request_and_create_organisation():
                    orgs_created += 1
            except Organisation.AlreadyExists as e:
                self.message_user(request, e, level=messages.ERROR)
        if orgs_created > 1:
            self.message_user(
                request,
                f"{orgs_created} organisations ont été créées.",
                level=messages.SUCCESS,
            )
        elif orgs_created == 1:
            self.message_user(
                request, "Une organisation a été créée.", level=messages.SUCCESS
            )

    accept_selected_requests.short_description = (
        "Accepter les demandes sélectionnées "
        "(créer les organisations et les aidants à former)"
    )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/accept/",
                self.admin_site.admin_view(self.accept_one_request),
                name="aidants_connect_habilitation_organisationrequest_accept",
            ),
            *super().get_urls(),
        ]

    def accept_one_request(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__accept_request_get(request, object_id)
        else:
            return self.__accept_request_post(request, object_id)

    def __accept_request_get(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        initial = {
            "email_subject": f"Votre demande d'habilitation n° {object.data_pass_id}",
            "email_body": f"{object.name} est maintenant habilitée.",
        }
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
            "form": AdminAcceptationForm(object, initial=initial),
        }

        return render(
            request,
            "aidants_connect_habilitation/admin/organisation_request/accept_form.html",
            view_context,
        )

    def __accept_request_post(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        form = AdminAcceptationForm(object, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()

        object.accept_request_and_create_organisation()

        subject = form.cleaned_data.get("email_subject")
        body_text = form.cleaned_data.get("email_body")

        text_message = body_text
        html_message = loader.render_to_string(
            "email/empty.html", {"content": mark_safe(linebreaks(body_text))}
        )

        recipients = set(object.aidant_requests.values_list("email", flat=True))
        recipients.add(object.manager.email)
        recipients.add(object.issuer.email)

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_ACCEPTANCE_FROM,
            recipient_list=list(recipients),
            subject=subject,
            message=text_message,
            html_message=html_message,
        )


if settings.AC_HABILITATION_FORM_ENABLED:
    admin_site.register(Issuer, IssuerAdmin)
    admin_site.register(OrganisationRequest, OrganisationRequestAdmin)
