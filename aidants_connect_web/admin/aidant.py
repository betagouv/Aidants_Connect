import logging
from gettext import ngettext

from django.contrib import admin
from django.contrib import messages as django_messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.urls import path, reverse_lazy
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.generic import FormView

from dateutil.relativedelta import relativedelta
from django_otp.plugins.otp_static.lib import add_static_token
from import_export import resources
from import_export.admin import ImportExportMixin
from import_export.fields import Field
from import_export.results import RowResult
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from aidants_connect.admin import VisibleToAdminMetier
from aidants_connect.utils import strtobool
from aidants_connect_common.admin import DepartmentFilter, RegionFilter
from aidants_connect_common.constants import JournalActionKeywords
from aidants_connect_habilitation.models import Manager
from aidants_connect_web.constants import OTP_APP_DEVICE_NAME
from aidants_connect_web.forms import (
    AidantChangeForm,
    AidantCreationForm,
    MassEmailActionForm,
)
from aidants_connect_web.models import (
    Aidant,
    AidantManager,
    CarteTOTP,
    HabilitationRequest,
    Journal,
    Organisation,
)

logger = logging.getLogger()


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
    totp_drift = Field(attribute="carte_totp__totp_device__drift")

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
            "conseiller_numerique",
            "phone",
            "carte_totp",
            "datapass_id",
            "respo_de_datapass_id",
            "token",
            "totp_drift",
        )

    def before_save_instance(self, instance: Aidant, row, **kwargs):
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

    def after_save_instance(self, instance: Aidant, row, **kwargs):
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
            totp_device = carte_totp.get_or_create_totp_device(confirmed=True)
            totp_device.save()


class AidantWithOTPAppFilter(SimpleListFilter):
    title = "Avec/sans application OTP"
    parameter_name = "with_otp_app"

    def lookups(self, request, model_admin):
        return [(True, "Avec une app OTP"), (False, "Sans app OTP")]

    def queryset(self, request, queryset: AidantManager):
        match strtobool(self.value(), None):
            case True:
                return queryset.filter(
                    totpdevice__name__startswith=OTP_APP_DEVICE_NAME % ""
                )
            case False:
                return queryset.filter(
                    ~Q(totpdevice__name__startswith=OTP_APP_DEVICE_NAME % "")
                )
            case _:
                return queryset


class AidantWithMandatsFilter(SimpleListFilter):
    title = "Avec/sans mandats"
    parameter_name = "with_mandates"

    def lookups(self, request, model_admin):
        return [("true", "Avec des mandats")]

    def queryset(self, request, queryset: AidantManager):
        if self.value() != "true":
            return queryset

        return queryset.filter(
            journal_entries__action=JournalActionKeywords.CREATE_ATTESTATION
        ).distinct()


class AidantDepartmentFilter(DepartmentFilter):
    filter_parameter_name = "organisations__zipcode"


class AidantInPreDesactivationZoneFilter(SimpleListFilter):
    title = "En attente de désactivation"
    parameter_name = "in_desactivation_zone"

    def value(self):
        return strtobool(super().value(), None)

    def lookups(self, request, model_admin):
        return [
            (False, "ne risque pas la désactivation"),
            (True, "Dans la zone de pré désactivation"),
        ]

    def queryset(self, request, queryset: AidantManager):
        match self.value():
            case False:
                return queryset.filter(
                    is_active=True, deactivation_warning_at__isnull=True
                )
            case True:
                return queryset.filter(
                    is_active=True, deactivation_warning_at__isnull=False
                )
            case _:
                return queryset


class AidantGoneTooLong(SimpleListFilter):
    title = "status de dernière connexion"
    parameter_name = "gone_too_long"
    relative_to = {"months": 5}

    def lookups(self, request, model_admin):
        return [
            (False, "Connectés recemment"),
            (True, "Actif mais non-connectés récemment"),
        ]

    def queryset(self, request, queryset: AidantManager):
        match strtobool(self.value(), None):
            case False:
                return queryset.filter(is_active=True).filter(
                    last_login__gt=timezone.now() - relativedelta(**self.relative_to)
                )
            case True:
                # Last connect more than 6 monts ago or never connected
                return queryset.filter(is_active=True).filter(
                    Q(
                        last_login__lte=timezone.now()
                        - relativedelta(**self.relative_to)
                    )
                    | Q(last_login=None)
                )
            case _:
                return queryset


class AidantNoActionTooLong(SimpleListFilter):
    title = "Suivi d'activité"
    parameter_name = "no_action_too_long"

    def lookups(self, request, model_admin):
        return [(True, "Pas dʼactivité depuis 90j+")]

    def queryset(self, request, queryset: AidantManager):
        match strtobool(self.value(), None):
            case True:
                return queryset.filter(Aidant.objects.q_without_activity_for_90_days())
            case _:
                return queryset


class AidantRegionFilter(RegionFilter):
    filter_parameter_name = "organisations__zipcode"


class AidantMassDeactivateFromMailFormView(FormView):
    form_class = MassEmailActionForm
    template_name = "aidants_connect_web/admin/aidants/mass_deactivation_form.html"
    success_url = reverse_lazy("otpadmin:aidants_connect_web_aidant_mass_deactivate")

    def get_context_data(self, **kwargs):
        return {
            **self.kwargs["model_admin"].admin_site.each_context(self.request),
            **super().get_context_data(**kwargs),
            "media": self.kwargs["model_admin"].media,
        }

    def form_valid(self, form):
        email_list = form.cleaned_data.get("email_list")
        processed_emails = set()

        for aidant in Aidant.objects.filter(email__in=email_list).all():
            aidant.deactivate()
            processed_emails.add(aidant.email)

        non_existing_emails = email_list - processed_emails

        if nb_non_existing := len(non_existing_emails):
            emails = (
                "".join([f"<p>{email}</p>" for email in sorted(non_existing_emails)])
                if nb_non_existing > 1
                else list(non_existing_emails)[0]
            )

            message = ngettext(
                "Nous n’avons trouvé aucun aidant à désactiver portant l’email "
                "suivant :%(emails)s.<br/>Ce profil n’a été désactivé.",
                "Nous n’avons trouvé aucun aidant à désactiver pour les %(count)d "
                "emails suivants :%(emails)s Ces profils n’ont pas été désactivés.",
                nb_non_existing,
            ) % {"count": nb_non_existing, "emails": emails}

            django_messages.warning(
                self.request,
                mark_safe(f"<section>{message}</section>"),
            )

        if nb_processed_emails := len(processed_emails):
            django_messages.success(
                self.request,
                ngettext(
                    "Le profil correspondant à l’email %(email)s a été désactivé.",
                    "Nous avons désactivé %(count)d profils.",
                    nb_processed_emails,
                )
                % {
                    "count": nb_processed_emails,
                    "email": list(processed_emails)[0],
                },
            )

        return super().form_valid(form)


class AidantAdmin(ImportExportMixin, VisibleToAdminMetier, DjangoUserAdmin):
    import_export_change_list_template = (
        "aidants_connect_web/admin/aidants/change_list.html"
    )

    # The forms to add and change `Aidant` instances
    form = AidantChangeForm
    add_form = AidantCreationForm
    actions = ["mass_deactivate", "add_habilitationrequest_to_manager"]
    raw_id_fields = ("responsable_de", "organisation", "organisations")
    readonly_fields = (
        "validated_cgu_version",
        "display_totp_device_status",
        "carte_totp",
        "display_mandates_count",
        "deactivation_warning_at",
    )

    # For bulk import
    resource_classes = [AidantResource]
    import_template_name = "aidants_connect_web/admin/import_export/import_aidant.html"

    # The fields to be used in displaying the `Aidant` model.
    # These override the definitions on the base `UserAdmin`
    # that references specific fields on `auth.User`.
    list_display = (
        "__str__",
        "id",
        "email",
        "organisation",
        "display_mandates_count",
        "carte_totp",
        "has_otp_app",
        "is_active",
        "can_create_mandats",
        "conseiller_numerique",
        "deactivation_warning_at",
        "created_at",
        "is_staff",
        "is_superuser",
        "totp_card_drift",
    )

    list_filter = (
        AidantRegionFilter,
        AidantDepartmentFilter,
        "is_active",
        "aidant_type",
        "can_create_mandats",
        "conseiller_numerique",
        AidantInPreDesactivationZoneFilter,
        AidantWithMandatsFilter,
        AidantGoneTooLong,
        AidantNoActionTooLong,
        AidantWithOTPAppFilter,
        "is_staff",
        "is_superuser",
    )
    search_fields = ("id", *DjangoUserAdmin.search_fields, "organisation__name")
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
                    "aidant_type",
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "password",
                    "carte_totp",
                    "display_totp_device_status",
                    "deactivation_warning_at",
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
                    "display_mandates_count",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "can_create_mandats",
                    "referent_non_aidant",
                    "conseiller_numerique",
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

    @admin.display(description="Carte TOTP Activée", boolean=True)
    def display_totp_device_status(self, obj):
        return obj.has_a_totp_device

    @admin.display(description="Nombre de mandats créés")
    def display_mandates_count(self, obj: Aidant):
        return Journal.objects.filter(
            action=JournalActionKeywords.CREATE_ATTESTATION, aidant=obj
        ).count()

    @admin.display(description="Application OTP", boolean=True)
    def has_otp_app(self, obj: Aidant):
        return obj.has_otp_app

    @admin.display(
        description="Drift de la carte OTP", ordering="carte_totp__totp_device__drift"
    )
    def totp_card_drift(self, obj: Aidant):
        return getattr(
            getattr(getattr(obj, "carte_totp", ""), "totp_device", ""), "drift", ""
        )

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

    def get_urls(self):
        return [
            path(
                "deactivate-from-emails/",
                self.admin_site.admin_view(
                    AidantMassDeactivateFromMailFormView.as_view()
                ),
                {"model_admin": self},
                name="aidants_connect_web_aidant_mass_deactivate",
            ),
            *super().get_urls(),
        ]

    # Ugh… When you save a model via admin forms it's not an atomic transaction.
    # So… You need to override save_related… https://stackoverflow.com/a/1925784
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        organisation = form.cleaned_data["organisation"]
        if organisation is not None:
            form.instance.organisations.add(
                *{*form.instance.responsable_de.all(), organisation}
            )

    def mass_deactivate(self, request: HttpRequest, queryset: QuerySet):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} profils ont été désactivés")

    mass_deactivate.short_description = "Désactiver les profils sélectionnés"

    @staticmethod
    def _add_habilitationrequest_to_manager(queryset: QuerySet):
        for one_manager in queryset.all():
            if (
                not one_manager.can_create_mandats
                and not HabilitationRequest.objects.filter(
                    email=one_manager.email
                ).exists()
            ):
                hr = HabilitationRequest.objects.create(
                    organisation=one_manager.organisation,
                    first_name=one_manager.first_name,
                    last_name=one_manager.last_name,
                    email=one_manager.email,
                    profession=one_manager.profession,
                )
                hab_manager = Manager.objects.filter(email=one_manager.email).first()
                if hab_manager:
                    hab_manager.habilitation_request = hr
                    hab_manager.save()

    def add_habilitationrequest_to_manager(
        self, request: HttpRequest, queryset: QuerySet
    ):
        self._add_habilitationrequest_to_manager(queryset)
        self.message_user(
            request, f"{queryset.count()} référent(s) peuvent s'inscrire en formation"
        )

    add_habilitationrequest_to_manager.short_description = (
        "Permettre à un/des référents de s'inscrire en formation"
    )
