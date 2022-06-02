from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin, StackedInline, TabularInline
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.urls import path, reverse
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe

from django_reverse_admin import ReverseInlineModelAdmin, ReverseModelAdmin

from aidants_connect.admin import (
    DepartmentFilter,
    RegionFilter,
    VisibleToAdminMetier,
    VisibleToTechAdmin,
    admin_site,
)
from aidants_connect_habilitation.forms import (
    AdminAcceptationOrRefusalForm,
    RequestMessageForm,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    IssuerEmailConfirmation,
    Manager,
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
        "email_verified",
    )
    readonly_fields = ("issuer_id",)
    inlines = (OrganisationRequestInline,)
    actions = ["resend_confirmation_emails"]

    def resend_confirmation_emails(self, request: HttpRequest, queryset: QuerySet):
        emails = IssuerEmailConfirmation.objects.filter(
            issuer__in=queryset, issuer__email_verified=False
        )
        for one_email in emails:
            one_email.send(request)

    resend_confirmation_emails.short_description = "Renvoyer les emails de confirmation"


class EmailConfirmationAdmin(VisibleToTechAdmin, ModelAdmin):
    pass


class AidantRequestInline(VisibleToAdminMetier, TabularInline):
    model = AidantRequest
    show_change_link = True
    extra = 0


class MessageInline(VisibleToAdminMetier, StackedInline):
    model = RequestMessage
    extra = 1


class ManagerReverseInlineModelAdmin(VisibleToAdminMetier, ReverseInlineModelAdmin):
    pass


class ManagerAdmin(VisibleToAdminMetier, ModelAdmin):
    fields = (
        "organisation",
        "first_name",
        "last_name",
        "email",
        "profession",
        "phone",
        "address",
        "zipcode",
        "city",
        "is_aidant",
    )
    readonly_fields = ("organisation",)

    list_display = (
        "first_name",
        "last_name",
        "email",
        "is_aidant",
        "organisation",
        "zipcode",
    )


class OrganisationRequestAdmin(VisibleToAdminMetier, ReverseModelAdmin):
    list_filter = ("status", RegionFilter, DepartmentFilter)
    list_display = ("name", "issuer", "status", "data_pass_id", "created_at")
    search_fields = ("data_pass_id", "name", "uuid")
    raw_id_fields = ("issuer", "organisation")
    fields = (
        "issuer",
        "created_at",
        "updated_at",
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
        "created_at",
        "updated_at",
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
    inline_reverse = [
        {
            "field_name": "manager",
            "admin_class": ManagerReverseInlineModelAdmin,
        }
    ]

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
                    self.send_acceptance_email(organisation_request)
                else:
                    self.message_user(
                        request,
                        f"""L'organisation {organisation_request.name} n'a pas été créée.
                        Vérifiez si la demande est bien en attente de validation.""",
                        level=messages.ERROR,
                    )
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
            path(
                "<path:object_id>/refuse/",
                self.admin_site.admin_view(self.refuse_one_request),
                name="aidants_connect_habilitation_organisationrequest_refuse",
            ),
            path(
                "<path:object_id>/require-changes/",
                self.admin_site.admin_view(self.require_changes_one_request),
                name="aidants_connect_habilitation_organisationrequest_requirechanges",
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

    def refuse_one_request(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__refuse_request_get(request, object_id)
        else:
            return self.__refuse_request_post(request, object_id)

    def require_changes_one_request(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__require_changes_request_get(request, object_id)
        else:
            return self.__require_changes_request_post(request, object_id)

    def __accept_request_get(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        email_body = loader.render_to_string(
            "email/demande_acceptee.txt", {"organisation": object}
        )
        email_subject = (
            "Aidants Connect - la demande d'habilitation n° "
            f"{object.data_pass_id} a été acceptée"
        )
        initial = {
            "email_subject": email_subject,
            "email_body": email_body,
        }
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
            "form": AdminAcceptationOrRefusalForm(object, initial=initial),
        }

        return render(
            request,
            "aidants_connect_habilitation/admin/organisation_request/accept_form.html",
            view_context,
        )

    def __accept_request_post(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        form = AdminAcceptationOrRefusalForm(object, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()

        object.accept_request_and_create_organisation()
        subject = form.cleaned_data.get("email_subject")
        body_text = form.cleaned_data.get("email_body")
        self.send_acceptance_email(object, body_text, subject)

        aidant_count = object.aidant_requests.count()
        if object.manager.is_aidant:
            aidant_count += 1
        self.message_user(
            request,
            (
                f"Tout s'est bien passé. La demande {object.data_pass_id} a "
                f"été acceptée. L'organisation {object.name} et le compte aidant "
                f"du responsable ont été créés. Les {aidant_count} aidants à former "
                "nécessaires ont été créés également."
            ),
        )

        return HttpResponseRedirect(
            reverse(
                "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
            )
        )

    def send_acceptance_email(self, object, body_text=None, subject=None):
        if body_text:
            text_message = body_text
        else:
            text_message = loader.render_to_string(
                "email/demande_acceptee.txt", {"organisation": object}
            )
        html_message = loader.render_to_string(
            "email/empty.html", {"content": mark_safe(linebreaks(text_message))}
        )

        if subject is None:
            subject = (
                "Aidants Connect - la demande d'habilitation n° "
                f"{object.data_pass_id} a été acceptée"
            )

        recipients = set(object.aidant_requests.values_list("email", flat=True))
        recipients.add(object.manager.email)
        recipients.add(object.issuer.email)

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=list(recipients),
            subject=subject,
            message=text_message,
            html_message=html_message,
        )

    def __refuse_request_get(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        email_body = loader.render_to_string(
            "email/demande_refusee.txt", {"organisation": object}
        )
        email_subject = (
            "Aidants Connect - la demande d'habilitation n° "
            f"{object.data_pass_id} a été refusée"
        )
        initial = {
            "email_subject": email_subject,
            "email_body": email_body,
        }
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
            "form": AdminAcceptationOrRefusalForm(object, initial=initial),
        }

        return render(
            request,
            "aidants_connect_habilitation/admin/organisation_request/refusal_form.html",
            view_context,
        )

    def __refuse_request_post(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        form = AdminAcceptationOrRefusalForm(object, data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()

        object.refuse_request()
        subject = form.cleaned_data.get("email_subject")
        body_text = form.cleaned_data.get("email_body")
        self.send_refusal_email(object, body_text, subject)

        self.message_user(
            request,
            (
                f"Tout s'est bien passé. La demande {object.data_pass_id} a "
                f"été refusée"
            ),
        )

        return HttpResponseRedirect(
            reverse(
                "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
            )
        )

    def send_refusal_email(self, object, body_text=None, subject=None):
        if body_text:
            text_message = body_text
        else:
            text_message = loader.render_to_string(
                "email/demande_refusee.txt", {"organisation": object}
            )
        html_message = loader.render_to_string(
            "email/empty.html", {"content": mark_safe(linebreaks(text_message))}
        )

        if subject is None:
            subject = (
                "Aidants Connect - la demande d'habilitation n° "
                f"{object.data_pass_id} a été refusée"
            )

        recipients = set(object.aidant_requests.values_list("email", flat=True))
        recipients.add(object.manager.email)
        recipients.add(object.issuer.email)

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=list(recipients),
            subject=subject,
            message=text_message,
            html_message=html_message,
        )

    def __require_changes_request_get(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        content = loader.render_to_string(
            "email/modifications_demandees.txt", {"organisation": object}
        )
        initial = {"content": content}
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
            "form": RequestMessageForm(initial=initial),
        }

        return render(
            request,
            "aidants_connect_habilitation/admin/organisation_request/require_changes.html",  # noqa
            view_context,
        )

    def __require_changes_request_post(self, request, object_id):
        object = OrganisationRequest.objects.get(id=object_id)
        form = RequestMessageForm(data=request.POST)
        if not form.is_valid():
            return HttpResponseNotAllowed()

        object.require_changes_request()
        content = form.cleaned_data.get("content")

        self.send_changes_required_message(object, content)

        self.message_user(
            request,
            (
                f"Tout s'est bien passé. La demande {object.data_pass_id} est "
                f"passé en statut modifications demandées."
            ),
        )

        return HttpResponseRedirect(
            reverse(
                "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
            )
        )

    def send_changes_required_message(self, object, content=None):
        message = RequestMessage(organisation=object, sender="AC", content=content)
        message.save()


if settings.AC_HABILITATION_FORM_ENABLED:
    admin_site.register(Issuer, IssuerAdmin)
    admin_site.register(Manager, ManagerAdmin)
    admin_site.register(OrganisationRequest, OrganisationRequestAdmin)
    admin_site.register(IssuerEmailConfirmation, EmailConfirmationAdmin)
