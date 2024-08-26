from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import (
    ModelAdmin,
    SimpleListFilter,
    StackedInline,
    TabularInline,
)
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.mail import send_mail
from django.db.models import Q, QuerySet
from django.db.utils import IntegrityError
from django.http import HttpRequest, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.urls import path, reverse
from django.utils.html import linebreaks, urlize
from django.utils.safestring import mark_safe

from django_reverse_admin import ReverseInlineModelAdmin, ReverseModelAdmin

from aidants_connect.admin import VisibleToAdminMetier, VisibleToTechAdmin, admin_site
from aidants_connect_common.admin import DepartmentFilter, RegionFilter
from aidants_connect_common.utils import render_email
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
    fields = ("id", "uuid", "status", "name", "type", "address", "zipcode", "city")
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(Issuer, site=admin_site)
class IssuerAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "email",
        "last_name",
        "first_name",
        "phone",
        "email_verified",
    )
    search_fields = (
        "email",
        "last_name",
        "first_name",
    )

    list_filter = ("email_verified",)
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


@admin.register(IssuerEmailConfirmation, site=admin_site)
class EmailConfirmationAdmin(VisibleToTechAdmin, ModelAdmin):
    pass


class AidantRequestInline(VisibleToAdminMetier, TabularInline):
    model = AidantRequest
    show_change_link = True
    extra = 0
    readonly_fields = ("habilitation_request",)


class MessageInline(VisibleToAdminMetier, StackedInline):
    model = RequestMessage
    extra = 1


class ManagerReverseInlineModelAdmin(VisibleToAdminMetier, ReverseInlineModelAdmin):
    readonly_fields = ("habilitation_request",)


@admin.register(Manager, site=admin_site)
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
        "city_insee_code",
        "department_insee_code",
        "is_aidant",
        "conseiller_numerique",
    )
    readonly_fields = ("organisation", "habilitation_request")

    list_display = (
        "first_name",
        "last_name",
        "email",
        "is_aidant",
        "conseiller_numerique",
        "organisation",
        "zipcode",
    )
    search_fields = (
        "email",
        "last_name",
        "first_name",
    )

    list_filter = ("is_aidant",)


class OrganisationPublicPrivateFilter(SimpleListFilter):
    title = "Structures Publiques / Privées INSEE"
    parameter_name = "public_private_insee"

    def value(self):
        return super().value()

    def lookups(self, request, model_admin):
        return [
            (1, "Structures publiques"),
            (2, "Structures privées"),
        ]

    def queryset(self, request, queryset):
        match self.value():
            case "1":
                return queryset.filter(
                    Q(legal_category__startswith="4")
                    | Q(legal_category__startswith="7")
                )
            case "2":
                return queryset.exclude(
                    Q(legal_category__startswith="4")
                    | Q(legal_category__startswith="7")
                )
            case _:
                return queryset


@admin.register(OrganisationRequest, site=admin_site)
class OrganisationRequestAdmin(VisibleToAdminMetier, ReverseModelAdmin):
    list_filter = (
        RegionFilter,
        DepartmentFilter,
        "status",
        "is_private_org",
        OrganisationPublicPrivateFilter,
    )
    list_display = (
        "name",
        "issuer",
        "status",
        "data_pass_id",
        "created_at",
        "legal_category",
    )
    search_fields = ("data_pass_id", "name", "uuid", "siret")
    raw_id_fields = ("issuer", "organisation")
    fields = (
        "issuer",
        "created_at",
        "updated_at",
        "uuid",
        "data_pass_id",
        "status",
        "organisation",
        "type",
        "type_other",
        "name",
        "siret",
        "legal_category",
        "address",
        "zipcode",
        "city",
        "city_insee_code",
        "department_insee_code",
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

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except IntegrityError as e:
            messages.set_level(request, messages.ERROR)
            if "partner_administration_if_org_is_private" in str(e):
                self.message_user(
                    request,
                    f"""L'organisation {obj.name} n'a pas été modifiée.
                        Merci de renseigner votre administration partenaire.""",
                    level=messages.ERROR,
                )

    def accept_selected_requests(self, request, queryset):
        orgs_created = 0
        for org_request in queryset:
            try:
                if org_request.accept_request_and_create_organisation():
                    orgs_created += 1
                    self.send_acceptance_email(request, org_request)
                else:
                    self.message_user(
                        request,
                        f"L'organisation {org_request.name} n'a pas été créée. "
                        "Vérifiez si la demande est bien en attente de validation.",
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
            path(
                "<path:object_id>/waiting/",
                self.admin_site.admin_view(self.in_waiting_one_request),
                name="aidants_connect_habilitation_organisationrequest_waiting",
            ),
            *super().get_urls(),
        ]

    def in_waiting_one_request(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__in_waiting_request_get(request, object_id)
        else:
            return self.__in_waiting_request_post(request, object_id)

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

    def __in_waiting_request_get(self, request, object_id):
        orga_request = OrganisationRequest.objects.get(id=object_id)
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": orga_request,
        }

        return render(
            request,
            "aidants_connect_habilitation/admin/organisation_request/in_waiting_form.html",  # noqa
            view_context,
        )

    def __in_waiting_request_post(self, request, object_id):
        orga_request = OrganisationRequest.objects.get(id=object_id)
        orga_request.go_in_waiting_again()
        self.message_user(
            request,
            (
                f"Tout s'est bien passé. La demande {orga_request.data_pass_id} a "
                f"été remise en attente"
            ),
        )

        redirect_path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        return HttpResponseRedirect(redirect_path)

    def __accept_request_get(self, request: HttpRequest, object_id):
        organisation = OrganisationRequest.objects.get(id=object_id)
        email_body = loader.render_to_string(
            "email/demande_acceptee.txt",
            {
                "organisation": organisation,
                "organisation_request_url": request.build_absolute_uri(
                    organisation.get_absolute_url()
                ),
                "habilitation_faq_formation": request.build_absolute_uri(
                    reverse("habilitation_faq_formation")
                ),
            },
        )
        email_subject = (
            "Aidants Connect - la demande d'habilitation n° "
            f"{organisation.data_pass_id} a été acceptée"
        )
        initial = {
            "email_subject": email_subject,
            "email_body": email_body,
        }
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": organisation,
            "form": AdminAcceptationOrRefusalForm(organisation, initial=initial),
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
        self.send_acceptance_email(request, object, body_text, subject)

        aidant_count = object.aidant_requests.count()
        if object.manager.is_aidant:
            aidant_count += 1
        self.message_user(
            request,
            (
                f"Tout s'est bien passé. La demande {object.data_pass_id} a "
                f"été acceptée. L'organisation {object.name} et le compte aidant "
                f"du référent ont été créés. Les {aidant_count} aidants à former "
                "nécessaires ont été créés également."
            ),
        )

        redirect_path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        return HttpResponseRedirect(redirect_path)

    def send_acceptance_email(
        self, request, organisation, body_text=None, subject=None
    ):
        body_text = body_text or loader.render_to_string(
            "email/demande_acceptee.txt",
            {
                "organisation": organisation,
                "organisation_request_url": request.build_absolute_uri(
                    organisation.get_absolute_url()
                ),
                "habilitation_faq_formation": request.build_absolute_uri(
                    reverse("habilitation_faq_formation")
                ),
            },
        )

        text_message, html_message = render_email(
            "email/empty.mjml",
            mjml_context={"content": mark_safe(urlize(linebreaks(body_text)))},
            text_context={"content": body_text},
        )

        if subject is None:
            subject = (
                "Aidants Connect - la demande d'habilitation n° "
                f"{organisation.data_pass_id} a été acceptée"
            )

        recipients = {organisation.issuer.email}
        if organisation.manager:
            recipients.add(organisation.manager.email)

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=list(recipients),
            subject=subject,
            message=text_message,
            html_message=html_message,
        )

    def __refuse_request_get(self, request, object_id):
        organisation = OrganisationRequest.objects.get(id=object_id)
        email_body = loader.render_to_string(
            "email/demande_refusee.txt", {"organisation": organisation}
        )
        email_subject = (
            "Aidants Connect - la demande d'habilitation n° "
            f"{organisation.data_pass_id} a été refusée"
        )
        initial = {
            "email_subject": email_subject,
            "email_body": email_body,
        }
        view_context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": organisation,
            "form": AdminAcceptationOrRefusalForm(organisation, initial=initial),
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

        redirect_path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        return HttpResponseRedirect(redirect_path)

    def send_refusal_email(self, organisation, body_text=None, subject=None):
        body_text = body_text or loader.render_to_string(
            "email/demande_refusee.txt", {"organisation": organisation}
        )

        text_message, html_message = render_email(
            "email/empty.mjml",
            mjml_context={"content": mark_safe(urlize(linebreaks(body_text)))},
            text_context={"content": body_text},
        )

        if subject is None:
            subject = (
                "Aidants Connect - la demande d'habilitation n° "
                f"{organisation.data_pass_id} a été refusée"
            )

        recipients = set(organisation.aidant_requests.values_list("email", flat=True))
        recipients.add(organisation.manager.email)
        recipients.add(organisation.issuer.email)

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
            "aidants_connect_habilitation/admin/organisation_request/modifications_demandees.txt",  # noqa
            {"organisation": object},
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

        redirect_path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta
        redirect_path = add_preserved_filters(
            {"preserved_filters": preserved_filters, "opts": opts}, redirect_path
        )
        return HttpResponseRedirect(redirect_path)

    def send_changes_required_message(self, object, content=None):
        message = RequestMessage(organisation=object, sender="AC", content=content)
        message.save()


@admin.register(AidantRequest, site=admin_site)
class AidantRequestAdmin(VisibleToTechAdmin, ModelAdmin):
    list_display = (
        "__str__",
        "email",
        "profession",
        "organisation",
        "conseiller_numerique",
    )
    raw_id_fields = ("organisation",)
    readonly_fields = ("habilitation_request",)
