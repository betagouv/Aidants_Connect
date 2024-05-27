import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.forms import ChoiceField
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from import_export import resources
from import_export.admin import ConfirmImportForm, ImportExportMixin, ImportForm
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from aidants_connect.admin import VisibleToAdminMetier
from aidants_connect_common.admin import DepartmentFilter, RegionFilter
from aidants_connect_common.models import Department
from aidants_connect_common.utils import build_url, render_email
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.forms import MassEmailActionForm
from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation

logger = logging.getLogger()


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
    organisation__city = Field(attribute="organisation__city", column_name="Ville")

    organisation_departement = Field(column_name="Département")
    organisation_region = Field(column_name="Région")

    class Meta:
        model = HabilitationRequest
        fields = set()

    def _get_department_from_zipcode(self, habilitation_request):
        zipcode = habilitation_request.organisation.zipcode or ""
        departements = Department.objects.filter(
            zipcode=Department.extract_dept_zipcode(zipcode)
        )
        return departements[0] if departements.exists() else None

    def dehydrate_organisation_region(self, habilitation_request):
        department: Department = self._get_department_from_zipcode(habilitation_request)
        if not department:
            return ""
        return department.region.name

    def dehydrate_organisation_departement(self, habilitation_request):
        department: Department = self._get_department_from_zipcode(habilitation_request)
        if not department:
            return ""
        return department.name


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

    def skip_row(self, instance, original, row, import_validation_errors=None):
        # do not change existing rows in database
        return not getattr(instance, "is_new", False)

    class Meta:
        model = HabilitationRequest
        fields = set()
        import_id_fields = ("email", "organisation__data_pass_id")


class HabilitationRequestImportDateFormationResource(resources.ModelResource):
    email = Field(attribute="email")
    organisation__data_pass_id = Field(
        attribute="organisation",
        widget=ForeignKeyWidget(Organisation, field="data_pass_id"),
        column_name="data_pass_id",
    )
    date_formation = Field(attribute="date_formation")

    def before_import_row(self, row, row_number=None, **kwargs):
        fieldname = "data_pass_id"
        if not (Organisation.objects.filter(data_pass_id=row[fieldname]).exists()):
            raise ValidationError("Organisation does not exist")
        return super().before_import_row(row, row_number, **kwargs)

    # skip new rows
    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not original.id:
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        instance.formation_done = True
        if instance.test_pix_passed:
            instance.validate_and_create_aidant()

    def after_save_instance(self, instance, using_transactions, dry_run):
        aidants_a_former = HabilitationRequest.objects.filter(email=instance.email)
        for aidant in aidants_a_former:
            if not aidant.formation_done:
                aidant.formation_done = True
                aidant.date_formation = instance.date_formation
                aidant.save()
                if aidant.test_pix_passed:
                    aidant.validate_and_create_aidant()
        return super().after_save_instance(instance, using_transactions, dry_run)

    class Meta:
        model = HabilitationRequest
        fields = set()
        import_id_fields = ("email", "organisation__data_pass_id")
        skip_unchanged = True


class HabilitationDepartmentFilter(DepartmentFilter):
    filter_parameter_name = "organisation__zipcode"


class HabilitationRequestRegionFilter(RegionFilter):
    filter_parameter_name = "organisation__zipcode"


class HabilitationRequestImportForm(ImportForm):
    import_choices = ChoiceField(
        label="Type d'import d'aidant à former",
        choices=(
            ("FORMATION_DATE", "Mettre à jour la date de formation"),
            ("OLD_FILES_IMPORT", "Importer des anciens fichiers"),
        ),
    )


class ConfirmHabilitationRequestImportForm(ConfirmImportForm):
    import_choices = ChoiceField(
        label="Type d'import d'aidant à former",
        choices=(
            ("FORMATION_DATE", "Mettre à jour la date de formation"),
            ("OLD_FILES_IMPORT", "Importer des anciens fichiers"),
        ),
    )


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
        HabilitationRequestRegionFilter,
        HabilitationDepartmentFilter,
        "status",
        "origin",
        "test_pix_passed",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "organisation__name",
        "organisation__data_pass_id",
    )
    ordering = ("email",)

    resource_classes = [HabilitationRequestResource]

    import_export_change_list_template = (
        "aidants_connect_web/admin/habilitation_request/change_list.html"
    )

    def get_import_resource_kwargs(self, request, form, *args, **kwargs):
        cleaned_data = getattr(form, "cleaned_data", False)
        if (
            isinstance(form, ConfirmHabilitationRequestImportForm)
            or isinstance(form, HabilitationRequestImportForm)
            and cleaned_data
        ):
            self.import_choices = cleaned_data["import_choices"]
        return kwargs

    def get_import_resource_classes(self):
        import_choices = getattr(self, "import_choices", False)
        if import_choices and import_choices == "FORMATION_DATE":
            return [HabilitationRequestImportDateFormationResource]
        elif import_choices and import_choices == "OLD_FILES_IMPORT":
            return [HabilitationRequestImportResource]

        return self.resource_classes

    def get_import_form(self):
        return HabilitationRequestImportForm

    def get_confirm_import_form(self):
        return ConfirmHabilitationRequestImportForm

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
                ReferentRequestStatuses.STATUS_PROCESSING,
                ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
                ReferentRequestStatuses.STATUS_NEW,
            )
        ).update(status=ReferentRequestStatuses.STATUS_REFUSED)
        for habilitation_request in queryset:
            self.send_refusal_email(habilitation_request)
        self.message_user(request, f"{rows_updated} demandes ont été refusées.")

    def send_refusal_email(self, aidant):
        text_message, html_message = render_email(
            "email/aidant_a_former_refuse.mjml", {"aidant": aidant}
        )

        subject = (
            "Aidants Connect - La demande d'ajout de l'aidant(e) "
            f"{aidant.first_name} {aidant.last_name} a été refusée."
        )

        recipients = [
            manager.email for manager in aidant.organisation.responsables.all()
        ]

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=recipients,
            subject=subject,
            message=text_message,
            html_message=html_message,
        )

    mark_refused.short_description = "Refuser les demandes sélectionnées"

    def mark_processing(self, request, queryset):
        habilitation_requests = queryset.filter(
            status__in=[
                ReferentRequestStatuses.STATUS_NEW,
                ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
            ]
        )

        for habilitation_request in habilitation_requests:
            habilitation_request.status = ReferentRequestStatuses.STATUS_PROCESSING
            habilitation_request.save()
        for habilitation_request in habilitation_requests:
            self.send_validation_email(habilitation_request)

        self.message_user(
            request,
            f"{habilitation_requests.count()} demandes sont maintenant en cours.",
        )

    mark_processing.short_description = (
        "Passer les demandes sélectionnées au statut "
        f"« {ReferentRequestStatuses.STATUS_PROCESSING.label} »"
    )

    def send_validation_email(self, aidant):
        text_message, html_message = render_email(
            "email/aidant_a_former_valide.mjml",
            {
                "aidant": aidant,
                "formation_url": build_url(reverse("habilitation_faq_formation")),
                "espace_referent_url": build_url(
                    reverse("espace_responsable_organisation")
                ),
            },
        )

        subject = (
            "Aidants Connect - La demande d'ajout de l'aidant(e) "
            f"{aidant.first_name} {aidant.last_name} a été validée !"
        )

        recipients = [
            manager.email for manager in aidant.organisation.responsables.all()
        ]

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=recipients,
            subject=subject,
            message=text_message,
            html_message=html_message,
        )

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
            "form": MassEmailActionForm(),
        }

        return render(
            request,
            "aidants_connect_web/admin/habilitation_request/mass-habilitation.html",
            context,
        )

    def __validate_from_email_post(self, request):
        form = MassEmailActionForm(request.POST)
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
                ReferentRequestStatuses.STATUS_PROCESSING,
                ReferentRequestStatuses.STATUS_NEW,
                ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
                ReferentRequestStatuses.STATUS_VALIDATED,
                ReferentRequestStatuses.STATUS_CANCELLED,
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
        ignored_emails = email_list - treated_emails
        context["treated_emails"] = treated_emails
        context["ignored_emails"] = ignored_emails
        context.update(self.__extract_more_precise_errors(ignored_emails))
        return render(
            request,
            "aidants_connect_web/admin/habilitation_request/mass-habilitation.html",
            context,
        )

    def __extract_more_precise_errors(self, ignored_emails):
        existing_emails = set(
            HabilitationRequest.objects.filter(email__in=ignored_emails).values_list(
                "email", flat=True
            )
        )
        non_existing_emails = set(ignored_emails - existing_emails)
        already_refused_emails = set(
            HabilitationRequest.objects.filter(
                email__in=existing_emails,
                status__in=(
                    ReferentRequestStatuses.STATUS_REFUSED,
                    ReferentRequestStatuses.STATUS_CANCELLED,
                ),
            ).values_list("email", flat=True)
        )
        undefined_error_emails = existing_emails - already_refused_emails
        return {
            "non_existing_emails": non_existing_emails,
            "already_refused_emails": already_refused_emails,
            "undefined_error_emails": undefined_error_emails,
        }
