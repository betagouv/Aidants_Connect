import base64
import logging
from gettext import ngettext as _
from io import BytesIO
from itertools import chain

from django.contrib import messages as django_messages
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, View

import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.views import (
    FormationRegistrationView as CommonFormationRegistrationView,
)
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_web.constants import (
    OTP_APP_DEVICE_NAME,
    AddAidantProfileChoice,
    HabilitationRequestCourseType,
    NotificationType,
    ReferentRequestStatuses,
    StructureChangeRequestStatuses,
)
from aidants_connect_web.decorators import (
    activity_required,
    responsable_logged_required,
    responsable_logged_with_activity_required,
)
from aidants_connect_web.forms import (
    AddAidantProfileChoiceForm,
    AddAppOTPToAidantForm,
    AddOrganisationReferentForm,
    CarteOTPSerialNumberForm,
    CarteTOTPValidationForm,
    ChangeAidantOrganisationsForm,
    CoReferentNonAidantRequestForm,
    NewHabilitationRequestForm,
    OrganisationRestrictDemarchesForm,
    RemoveCardFromAidantForm,
    StructureChangeRequestForm,
    StructureChangeRequestFormSet,
)
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    CoReferentNonAidantRequest,
    HabilitationRequest,
    Journal,
    Notification,
    Organisation,
    StructureChangeRequest,
)
from aidants_connect_web.presenters import AidantFormationPresenter

logger = logging.getLogger()


class ReferentCannotManageAidantResponseMixin:
    def referent_cannot_manage_aidant_response(self):
        django_messages.error(
            self.request,
            "Erreur : ce profil aidant nʼexiste pas ou nʼest pas membre "
            "de votre organisation active. "
            "Si ce profil existe et que vous faites partie de ses référents, "
            "veuillez changer dʼorganisation pour le gérer.",
        )
        return redirect("espace_referent:organisation")


@responsable_logged_required
# We don't want to check activity on POST route
@responsable_logged_with_activity_required(method_name="get")
class OrganisationView(DetailView, FormView):
    template_name = "aidants_connect_web/espace_responsable/organisation.html"
    context_object_name = "organisation"
    model = Organisation
    form_class = OrganisationRestrictDemarchesForm
    success_url = reverse_lazy("espace_referent:organisation")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        # Needed when following the FormView path
        self.organisation = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not hasattr(self, "object"):
            self.object = get_object_or_404(
                Organisation,
                pk=self.referent.organisation.pk,
                responsables=self.referent,
            )

        return self.object

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "referent": self.referent,
            "referent_notifications": Notification.objects.get_displayable_for_user(
                self.referent
            ),
            "notification_type": NotificationType,
            "perimetres_form": super().get_form(),
        }

    def get_initial(self):
        return {"demarches": self.referent.organisation.allowed_demarches}

    def form_valid(self, form):
        self.organisation.allowed_demarches = form.cleaned_data["demarches"]
        self.organisation.save(update_fields=("allowed_demarches",))
        return super().form_valid(form)


@responsable_logged_required
# We don't want to check activity on POST route
@responsable_logged_with_activity_required(method_name="get")
class HomeView(DetailView, FormView):
    template_name = "aidants_connect_web/espace_responsable/home.html"
    context_object_name = "organisation"
    model = Organisation
    form_class = OrganisationRestrictDemarchesForm
    success_url = reverse_lazy("espace_referent:organisation")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not hasattr(self, "object"):
            self.object = get_object_or_404(
                Organisation,
                pk=self.referent.organisation.pk,
                responsables=self.referent,
            )

        return self.object

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "referent": self.referent,
        }


@responsable_logged_required
# We don't want to check activity on POST route
@responsable_logged_with_activity_required(method_name="get")
class ReferentsView(DetailView, FormView):
    template_name = "aidants_connect_web/espace_responsable/referents.html"
    context_object_name = "organisation"
    model = Organisation
    form_class = OrganisationRestrictDemarchesForm
    success_url = reverse_lazy("espace_referent:referents")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        # Needed when following the FormView path
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        self.organisation: Organisation = self.referent.organisation

        if not self.organisation:
            django_messages.error(
                self.request, "Erreur : vous n'êtes pas rattaché à une organisation."
            )
            return redirect("espace_aidant:home")
        return self.organisation

    def get_context_data(self, **kwargs):
        referents_qs = (
            self.object.responsables.exclude(pk=self.referent.pk)
            .order_by("last_name")
            .prefetch_related("carte_totp")
        )
        organisation_active_referents = [
            self.referent,
            *sorted(
                chain(
                    referents_qs.filter(is_active=True).order_by(
                        "last_name", "first_name"
                    ),
                    CoReferentNonAidantRequest.objects.filter(
                        organisation=self.organisation
                    ).exclude(status=ReferentRequestStatuses.STATUS_VALIDATED),
                ),
                key=lambda item: item.get_full_name().casefold(),
            ),
        ]
        organisation_inactive_referents = referents_qs.filter(is_active=False)

        return {
            **super().get_context_data(**kwargs),
            "referent": self.referent,
            "referent_notifications": Notification.objects.get_displayable_for_user(
                self.referent
            ),
            "notification_type": NotificationType,
            "organisation_active_referents": organisation_active_referents,
            "organisation_inactive_referents": organisation_inactive_referents,
            "perimetres_form": super().get_form(),
        }

    def get_initial(self):
        return {"demarches": self.referent.organisation.allowed_demarches}

    def form_valid(self, form):
        self.organisation.allowed_demarches = form.cleaned_data["demarches"]
        self.organisation.save(update_fields=("allowed_demarches",))
        return super().form_valid(form)


@responsable_logged_required
# We don't want to check activity on POST route
@responsable_logged_with_activity_required(method_name="get")
class AidantsView(DetailView, FormView):
    template_name = "aidants_connect_web/espace_responsable/aidants.html"
    context_object_name = "organisation"
    model = Organisation
    success_url = reverse_lazy("espace_referent:aidants")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        # Needed when following the FormView path
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return (
            AddOrganisationReferentForm
            if "candidate" in self.request.POST
            else OrganisationRestrictDemarchesForm
        )

    def get_form_kwargs(self):
        return (
            {**super().get_form_kwargs(), "organisation": self.organisation}
            if "candidate" in self.request.POST
            else {**super().get_form_kwargs()}
        )

    def get_object(self, queryset=None):
        self.organisation: Organisation = self.referent.organisation

        if not self.organisation:
            django_messages.error(
                self.request, "Erreur : vous n'êtes pas rattaché à une organisation."
            )
            return redirect("espace_aidant:home")
        return self.organisation

    def get_eligibility_validated_requests(self):
        return (
            self.object.habilitation_requests.filter(
                status__in=[
                    ReferentRequestStatuses.STATUS_PROCESSING.value,
                    ReferentRequestStatuses.STATUS_PROCESSING_P2P.value,
                ],
                created_by_fne=False,
            )
            .exclude(id_fne__isnull=False)
            .order_by("status", "last_name")
        )

    def get_context_data(self, **kwargs):
        aidantq_qs = self.object.aidants_not_responsables.order_by(
            "last_name"
        ).prefetch_related("carte_totp")

        organisation_active_aidants = aidantq_qs.filter(is_active=True)
        organisation_inactive_aidants = aidantq_qs.filter(is_active=False)

        unregistrable_requests = self.object.habilitation_requests.filter(
            status__in=[
                ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
                ReferentRequestStatuses.STATUS_NEW.value,
                ReferentRequestStatuses.STATUS_REFUSED.value,
                ReferentRequestStatuses.STATUS_CANCELLED.value,
                ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE.value,
            ],
            created_by_fne=False,
        ).order_by("status", "last_name")

        eligibility_validated_requests = self.get_eligibility_validated_requests()
        pending_structure_requests = self.object.get_pending_structure_change_requests()
        closed_structure_requests = self.object.get_closed_structure_change_requests()

        return {
            **super().get_context_data(**kwargs),
            "referent": self.referent,
            "referent_notifications": Notification.objects.get_displayable_for_user(
                self.referent
            ),
            "notification_type": NotificationType,
            "organisation_active_aidants": organisation_active_aidants,
            "organisation_inactive_aidants": organisation_inactive_aidants,
            "perimetres_form": super().get_form(),
            "eligibility_validated_requests": eligibility_validated_requests,
            "unregistrable_requests": unregistrable_requests,
            "pending_structure_requests": pending_structure_requests,
            "closed_structure_requests": closed_structure_requests,
        }

    def form_valid(self, form):
        if isinstance(form, AddOrganisationReferentForm):
            new_responsable = form.cleaned_data["candidate"]
            new_responsable.responsable_de.add(self.organisation)
            new_responsable.save()
            django_messages.success(
                self.request,
                (
                    f"{new_responsable} a été désigné comme "
                    f"responsable de l’organisation {self.organisation} avec succès."
                ),
            )
        return super().form_valid(form)


@responsable_logged_with_activity_required
class OrganisationResponsables(FormView):
    template_name = "aidants_connect_web/espace_responsable/responsables.html"
    success_url = reverse_lazy("espace_referent:referents")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.organisation = get_object_or_404(
            Organisation, pk=kwargs.get("organisation_id"), responsables=self.referent
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "organisation": self.organisation}

    def get_form_class(self):
        return (
            AddOrganisationReferentForm
            if "candidate" in self.request.POST
            else CoReferentNonAidantRequestForm
        )

    def form_valid(self, form):
        if isinstance(form, AddOrganisationReferentForm):
            new_responsable = form.cleaned_data["candidate"]
            new_responsable.responsable_de.add(self.organisation)
            new_responsable.save()
            django_messages.success(
                self.request,
                (
                    f"{new_responsable} a été désigné comme "
                    f"responsable de l’organisation {self.organisation} avec succès."
                ),
            )
        else:
            instance = form.save()
            django_messages.success(
                self.request,
                (
                    f"Votre demande pour ajouter {instance.get_full_name()} au "
                    f"poste de referent non-aidant de {self.organisation} a été "
                    "transmise avec succès. Elle va faire l'objet d'un examen "
                    "de la part de nos équipes."
                ),
            )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({"user": self.referent, "organisation": self.organisation})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class AidantView(ReferentCannotManageAidantResponseMixin, TemplateView):
    template_name = "aidants_connect_web/espace_responsable/aidant.html"
    presenter_formation = AidantFormationPresenter

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            return self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Récupérer les organisations communes
        referent_orgs = self.referent.responsable_de.all()
        # Inclure les organisations où l'aidant est membre OU référent (sans doublons)
        aidant_member_orgs = self.aidant.organisations.all()
        aidant_referent_orgs = self.aidant.responsable_de.all()
        all_aidant_org_ids = set(aidant_member_orgs.values_list("pk", flat=True)) | set(
            aidant_referent_orgs.values_list("pk", flat=True)
        )
        common_organisations = referent_orgs.filter(pk__in=all_aidant_org_ids)

        is_aidant_referent_of_current_org = self.aidant.responsable_de.filter(
            pk=self.referent.organisation.pk
        ).exists()

        presenter_formation = self.presenter_formation(self.aidant)

        kwargs.update(
            {
                "aidant": self.aidant,
                "responsable": self.referent,
                "referent_orgs": referent_orgs,
                "organisation": self.referent.organisation,
                "form": ChangeAidantOrganisationsForm(self.referent, self.aidant),
                "common_organisations": common_organisations,
                "is_aidant_referent_of_current_org": is_aidant_referent_of_current_org,
                "formation": presenter_formation,
            }
        )
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class GenerateAidantFormationAttestation(ReferentCannotManageAidantResponseMixin, View):
    """
    Lets a structure referent download the formation
    attestation PDF for a managed aidant.
    """

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            return self.referent_cannot_manage_aidant_response()
        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.aidant.can_create_mandats:
            django_messages.error(
                request,
                (
                    "Cet aidant ne peut pas recevoir dʼattestation "
                    "de formation Aidants Connect.",
                ),
            )
            return redirect(
                "espace_referent:aidant_detail", kwargs={"aidant_id": self.aidant.pk}
            )
        self.aidant.generate_attestation()
        return HttpResponse(
            self.aidant.attestation.read(),
            content_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{self.aidant.attestation.name}"'
                )
            },
        )


@responsable_logged_with_activity_required
class RemoveCardFromAidant(ReferentCannotManageAidantResponseMixin, FormView):
    template_name = "aidants_connect_web/espace_responsable/aidant_remove_card.html"
    form_class = RemoveCardFromAidantForm
    success_url = reverse_lazy("espace_referent:aidants")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            return self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        if not self.aidant.has_a_carte_totp:
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "responsable": self.referent,
        }

    def form_valid(self, form):
        sn = self.aidant.carte_totp.serial_number

        carte = CarteTOTP.objects.get(serial_number=sn)

        with transaction.atomic():
            carte.unlink_aidant()

            Journal.log_card_dissociation(
                self.referent, self.aidant, sn, form.cleaned_data["reason"]
            )

        django_messages.success(
            self.request,
            (
                f"La carte {sn} a été séparée du compte "
                f"de l’aidant {self.aidant.get_full_name()} avec succès."
            ),
        )

        return super().form_valid(form)


@responsable_logged_with_activity_required
class AddAppOTPToAidant(ReferentCannotManageAidantResponseMixin, FormView):
    template_name = "aidants_connect_web/espace_responsable/app_otp_confirm.html"
    form_class = AddAppOTPToAidantForm
    success_url = reverse_lazy("espace_referent:organisation")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            return self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        if self.aidant.has_otp_app:
            django_messages.warning(
                request,
                "Attention : il existe déjà une carte OTP numérique liée à ce profil. "
                "Si vous voulez en attacher une nouvelle, veuillez supprimer "
                "l’anciennne.",
            )
            return HttpResponseRedirect(self.get_success_url())

        if not self.aidant.is_active:
            django_messages.warning(
                request,
                f"Attention : le profil de {self.aidant.get_full_name()} désactivé. "
                "Il est impossible de lui lier attacher une nouvelle carte OTP "
                "numérique.",
            )
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.otp_device = TOTPDevice(
            user=self.aidant,
            name=OTP_APP_DEVICE_NAME % self.aidant.pk,
            confirmed=False,
        )
        request.session["otp_device"] = model_to_dict(self.otp_device)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.otp_device = TOTPDevice(
            **self.get_model_kwargs(request.session["otp_device"])
        )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.otp_device.confirmed = True
                self.otp_device.save()

                Journal.log_card_association(
                    self.referent, self.aidant, self.otp_device.name
                )
            # Clean session
            self.request.session.pop("otp_device")

            from aidants_connect_web.signals import card_associated_to_aidant

            card_associated_to_aidant.send(None, otp_device=self.otp_device)

        except Exception:
            message = (
                "Une erreur s’est produite lors de la sauvegarde de la carte numérique."
            )
            logger.exception(message)
            django_messages.error(self.request, message)

        return super().form_valid(form)

    @staticmethod
    def get_model_kwargs(fields: dict):
        result = {}
        for field_name, field_value in fields.items():
            field = TOTPDevice._meta.get_field(field_name)

            if field.many_to_one:
                result[field.attname] = int(field_value)
            else:
                result[field_name] = field_value
        return result

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "otp_device": self.otp_device}

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "otp_device_qr_code_href": (
                f"data:image/png;base64,{self.get_image_base_64()}"
            ),
        }

    def get_image_base_64(self):
        stream = BytesIO()
        img = qrcode.make(self.otp_device.config_url, box_size=7, border=4)
        img.save(stream, "PNG")
        return base64.b64encode(stream.getvalue()).decode("utf-8")


@responsable_logged_with_activity_required
class RemoveAppOTPFromAidant(ReferentCannotManageAidantResponseMixin, DeleteView):
    template_name = "aidants_connect_web/espace_responsable/app_otp_remove.html"
    success_url = reverse_lazy("espace_referent:organisation")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            return self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        if not self.aidant.has_otp_app:
            return HttpResponseRedirect(reverse("espace_referent:organisation"))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "aidant": self.aidant}

    def get_object(self, queryset=None):
        return self.aidant.totpdevice_set.filter(
            name=OTP_APP_DEVICE_NAME % self.aidant.pk
        )

    def form_valid(self, form):
        card_name = self.object.first().name
        response = super().form_valid(form)
        Journal.log_card_dissociation(
            self.referent, self.aidant, card_name, "no reason"
        )
        return response


@responsable_logged_with_activity_required
class RemoveAidantFromOrganisationView(
    ReferentCannotManageAidantResponseMixin, TemplateView
):
    template_name = "aidants_connect_web/espace_responsable/confirm-remove-aidant-from-organisation.html"  # noqa: E501

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.organisation: Organisation = get_object_or_404(
            Organisation, pk=kwargs["organisation_id"]
        )
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            self.referent_cannot_manage_aidant_response()
        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        result = self.aidant.remove_from_organisation(self.organisation)
        if result is True:
            django_messages.success(
                request,
                (
                    f"{self.aidant.get_full_name()} a été retirée de "
                    f"{self.organisation.name} avec succès."
                ),
            )
        else:
            django_messages.success(
                request,
                (
                    f"Le profil de {self.aidant.get_full_name()}"
                    "a été désactivé avec succès."
                ),
            )

        # Vérifier si l'aidant est référent de cette organisation
        if self.aidant in self.organisation.responsables.all():
            return redirect("espace_referent:referents")
        else:
            return redirect("espace_referent:aidants")

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant, "organisation": self.organisation})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class ReactivateAidantFromOrganisationView(
    ReferentCannotManageAidantResponseMixin, TemplateView
):
    template_name = "aidants_connect_web/espace_responsable/confirm-reactivate-aidant-from-organisation.html"  # noqa: E501

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.organisation: Organisation = get_object_or_404(
            Organisation, pk=kwargs["organisation_id"]
        )
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            self.referent_cannot_manage_aidant_response()
        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"{self.aidant.get_full_name()} est un aidant actif"
                    f"il ne peut être activé à nouveau"
                ),
            )
        else:
            self.aidant.is_active = True
            self.aidant.save()
            django_messages.success(
                request,
                (f"{self.aidant.get_full_name()} a été activé à nouveau avec succés "),
            )

        # Vérifier si l'aidant est référent de cette organisation
        if self.aidant in self.organisation.responsables.all():
            return redirect("espace_referent:referents")
        else:
            return redirect("espace_referent:aidants")

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant, "organisation": self.organisation})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class ChangeAidantOrganisations(ReferentCannotManageAidantResponseMixin, FormView):
    form_class = ChangeAidantOrganisationsForm
    success_url = reverse_lazy("espace_referent:organisation")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            self.referent_cannot_manage_aidant_response()
        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # GET is not used
        return self.http_method_not_allowed(request, *args, **kwargs)

    def form_invalid(self, form):
        django_messages.error(self.request, str(form.errors["organisations"]))
        return redirect("espace_referent:aidant_detail", aidant_id=self.aidant.id)

    def form_valid(self, form):
        responsable_organisations = self.referent.responsable_de.all()
        aidant_organisations = self.aidant.organisations.all()
        posted_organisations = form.cleaned_data["organisations"]

        unrelated_organisations = aidant_organisations.difference(
            responsable_organisations
        )
        self.aidant.set_organisations(
            unrelated_organisations.union(posted_organisations)
        )

        message = _(
            "Le compte de %(u)s a été rattaché aux organisations %(org)s avec succès",
            "Le compte de %(u)s a été rattaché aux organisations %(org)s avec succès",
            len(posted_organisations),
        ) % {
            "u": self.aidant,
            "org": ", ".join(org.name for org in posted_organisations),
        }

        django_messages.success(self.request, message)

        return super().form_valid(form)

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "responsable": self.referent,
            "aidant": self.aidant,
        }


@responsable_logged_with_activity_required
class ChooseTOTPDevice(ReferentCannotManageAidantResponseMixin, TemplateView):
    template_name = "aidants_connect_web/espace_responsable/choose-totp-device.html"

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            self.referent_cannot_manage_aidant_response()
        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        option_unavailable_text = (
            "Ce profil est désactivé et n'est associé à aucune carte %s."
            "Aucune action n'est disponible."
        )
        physical_option_available = (
            self.aidant.is_active or self.aidant.has_a_carte_totp
        )
        physical_option_unavailable_text = option_unavailable_text % "physique"

        digital_option_available = self.aidant.has_otp_app or self.aidant.is_active
        digital_option_unavailable_text = option_unavailable_text % "numérique"

        kwargs.update(
            {
                "aidant": self.aidant,
                "referent": self.referent,
                "physical_option_available": physical_option_available,
                "physical_option_unavailable_text": physical_option_unavailable_text,
                "digital_option_available": digital_option_available,
                "digital_option_unavailable_text": digital_option_unavailable_text,
            }
        )
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class AssociateAidantCarteTOTP(ReferentCannotManageAidantResponseMixin, FormView):
    form_class = CarteOTPSerialNumberForm
    template_name = "aidants_connect_web/espace_responsable/write-carte-totp-sn.html"

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        if self.aidant.has_a_carte_totp:
            django_messages.error(
                request,
                (
                    f"Erreur : le compte de {self.aidant.get_full_name()} est déjà "
                    f"lié à une carte Aidants Connect. Vous devez d’abord retirer la "
                    f"carte de son compte avant de pouvoir en lier une nouvelle."
                ),
            )

            return redirect("espace_referent:aidant_detail", aidant_id=self.aidant.id)

        if not self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"Erreur : le compte de {self.aidant.get_full_name()} est désactivé"
                    ". Il est impossible de lui attacher une nouvelle carte "
                    "Aidant Connect"
                ),
            )

            return redirect("espace_referent:aidant_detail", aidant_id=self.aidant.id)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "espace_referent:validate_totp", kwargs={"aidant_id": self.aidant.id}
        )

    def form_valid(self, form):
        serial_number = form.cleaned_data["serial_number"]
        try:
            carte_totp = CarteTOTP.objects.get(serial_number=serial_number)

            with transaction.atomic():
                carte_totp.aidant = self.aidant
                carte_totp.save()
                carte_totp.get_or_create_totp_device()
                Journal.log_card_association(self.referent, self.aidant, serial_number)

            from aidants_connect_web.signals import card_associated_to_aidant

            card_associated_to_aidant.send(None, otp_device=carte_totp.totp_device)

        except Exception:
            message = "Une erreur s’est produite lors de la sauvegarde de la carte."
            logger.exception(message)
            django_messages.error(self.request, message)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant, "responsable": self.referent})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class ValidateAidantCarteTOTP(ReferentCannotManageAidantResponseMixin, FormView):
    form_class = CarteTOTPValidationForm
    template_name = "aidants_connect_web/espace_responsable/validate-carte-totp.html"

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        if not self.aidant.has_a_carte_totp:
            django_messages.error(
                request,
                (
                    "Erreur : impossible de trouver une carte Aidants Connect "
                    f"associée au compte de {self.aidant.get_full_name()}."
                    "Vous devez d’abord lier une carte à son compte."
                ),
            )

            return redirect("espace_referent:aidant_detail", aidant_id=self.aidant.id)

        if not self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"Erreur : le profil de {self.aidant.get_full_name()} est désactivé"
                    ". Il est impossible de valider la carte Aidants Connect "
                    "qui lui est associée."
                ),
            )

            return redirect("espace_referent:aidant_detail", aidant_id=self.aidant.id)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "espace_referent:aidant_detail", kwargs={"aidant_id": self.aidant.id}
        )

    def form_valid(self, form):
        token = form.cleaned_data["otp_token"]
        totp_device = TOTPDevice.objects.get(
            key=self.aidant.carte_totp.seed, user=self.aidant
        )

        if not totp_device.verify_token(token):
            form.add_error("otp_token", "Ce code n’est pas valide.")
            return self.form_invalid(form)

        with transaction.atomic():
            totp_device.tolerance = 1
            totp_device.confirmed = True
            totp_device.save()
            Journal.log_card_validation(
                self.referent, self.aidant, self.aidant.carte_totp.serial_number
            )
            # check if the validation request is for the référent
            if self.referent.pk == self.aidant.pk:
                # get all organisations aidant is référent
                valid_organisation_requests = OrganisationRequest.objects.filter(
                    organisation__in=self.referent.responsable_de.all()
                )
                # close all validated requests
                for organisation_request in valid_organisation_requests:
                    if (
                        organisation_request.status
                        == RequestStatusConstants.VALIDATED.name
                    ):
                        organisation_request.status = RequestStatusConstants.CLOSED.name
                        organisation_request.save()
        django_messages.success(
            self.request,
            (f"Le compte de {self.aidant.get_full_name()} a été préparé avec succès"),
        )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant})
        return super().get_context_data(**kwargs)


SESSION_KEY_ADD_AIDANT_WIZARD = "add_aidant_wizard"


class AddAidantWizardMixin:
    """Shared session-management logic for the add-aidant wizard views."""

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.referent: Aidant = request.user
        self._wizard = request.session.get(SESSION_KEY_ADD_AIDANT_WIZARD) or {}

    def _wizard_step(self):
        raise NotImplementedError

    def _back_url(self):
        return None

    def _profile_choice(self):
        return self._wizard.get("profile_choice")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            wizard_step=self._wizard_step(),
            wizard_total_steps=3,
            wizard_profile_choice=self._profile_choice(),
            referent=self.referent,
            wizard_back_url=self._back_url(),
        )
        return ctx

    def _save_wizard(self, **kwargs):
        w = dict(self._wizard)
        w.update(kwargs)
        self.request.session[SESSION_KEY_ADD_AIDANT_WIZARD] = w
        self._wizard = w

    def _clear_wizard(self):
        if SESSION_KEY_ADD_AIDANT_WIZARD in self.request.session:
            del self.request.session[SESSION_KEY_ADD_AIDANT_WIZARD]
        self._wizard = {}

    def _reset_wizard(self):
        self.request.session[SESSION_KEY_ADD_AIDANT_WIZARD] = {}
        self._wizard = {}

    def _has_valid_profile_choice(self):
        return self._profile_choice() in AddAidantProfileChoice.values

    def _is_ready_for_confirmation(self):
        if not self._has_valid_profile_choice():
            return False
        if not self._wizard.get("ready_for_confirmation"):
            return False
        profile = self._profile_choice()
        if profile == AddAidantProfileChoice.NOT_YET_TRAINED:
            return bool(self._wizard.get("classic_data"))
        if profile == AddAidantProfileChoice.ALREADY_TRAINED:
            return bool(self._wizard.get("structure_change_data"))
        return False

    def _no_cache_response(self, response):
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    def _serialize_classic_data(self, cleaned_data):
        """Build session-serializable dict from
        NewHabilitationRequestForm.cleaned_data."""
        course_type = cleaned_data.get("course_type") or {}
        hab_list = cleaned_data.get("habilitation_requests") or []
        return {
            "course_type": {
                "type": course_type.get("type"),
                "email_formateur": course_type.get("email_formateur"),
            },
            # Store all forms (including empty slots)
            # so back navigation restores the right count
            "habilitation_requests": [
                {
                    "email": h.get("email") or "",
                    "first_name": h.get("first_name", ""),
                    "last_name": h.get("last_name", ""),
                    "profession": h.get("profession", ""),
                    "organisation_id": (
                        h.get("organisation").pk if h.get("organisation") else None
                    ),
                    "conseiller_numerique": h.get("conseiller_numerique", False),
                }
                for h in hab_list
            ],
        }

    def _create_classic_requests(self, classic_data):

        course_type = classic_data.get("course_type") or {}
        type_val = course_type.get("type")
        email_formateur = course_type.get("email_formateur")
        hab_forms = classic_data.get("habilitation_requests") or []
        for h in hab_forms:
            if not h.get("email") or not h.get("organisation_id"):
                continue
            HabilitationRequest.objects.create(
                organisation_id=h["organisation_id"],
                email=h["email"],
                first_name=h.get("first_name", ""),
                last_name=h.get("last_name", ""),
                profession=h.get("profession", ""),
                conseiller_numerique=bool(h.get("conseiller_numerique", False)),
                course_type=(
                    int(type_val) if type_val else HabilitationRequestCourseType.CLASSIC
                ),
                email_formateur=email_formateur or None,
                origin=HabilitationRequest.ORIGIN_RESPONSABLE,
            )

    def _new_habilitation_form_kwargs(self):
        return {
            "form_kwargs": {
                "habilitation_requests": {"form_kwargs": {"referent": self.referent}}
            }
        }


@method_decorator(activity_required, name="get")
@responsable_logged_required
class AddAidantProfileChoiceView(AddAidantWizardMixin, FormView):
    """Step 1: choose not-yet-trained vs already-habilitated aidants to add."""

    template_name = (
        "aidants_connect_web/espace_responsable/add-aidant-wizard-step1.html"
    )
    form_class = AddAidantProfileChoiceForm

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "organisation": self.referent.organisation,
        }

    def _wizard_step(self):
        return 1

    def get(self, request, *args, **kwargs):
        self._reset_wizard()
        return self._no_cache_response(super().get(request, *args, **kwargs))

    def form_valid(self, form):
        profile = int(form.cleaned_data["profile"])
        self._reset_wizard()
        self._save_wizard(profile_choice=profile)
        if profile == AddAidantProfileChoice.NOT_YET_TRAINED:
            return redirect(reverse("espace_referent:aidant_new_untrained"))
        return redirect(reverse("espace_referent:aidant_new_trained"))


@method_decorator(activity_required, name="get")
@responsable_logged_required
class AddAidantTrainedView(AddAidantWizardMixin, TemplateView):
    """Step 2a: enter already-trained aidants (structure change formset)."""

    template_name = (
        "aidants_connect_web/espace_responsable/add-aidant-wizard-step2-trained.html"
    )

    def _wizard_step(self):
        return 2

    def _get_structure_change_formset(self, data=None, initial=None):
        return StructureChangeRequestFormSet(
            data=data,
            queryset=StructureChangeRequest.objects.none(),
            referent=self.referent,
            initial=initial,
        )

    def _build_trained_initial_from_session(self):
        """Build formset initial list from session structure_change_data
        for back navigation."""
        structure_data = self._wizard.get("structure_change_data") or []
        if not structure_data:
            return None
        initial = []
        for item in structure_data:
            new_email = (item.get("new_email") or "").strip()
            initial.append(
                {
                    "email": item.get("email") or "",
                    "new_email": new_email,
                    "email_will_change": bool(new_email),
                    "email_lookup_done": True,
                }
            )
        return initial if initial else None

    def _guard_profile_or_redirect(self):
        if self._profile_choice() != AddAidantProfileChoice.ALREADY_TRAINED:
            self._clear_wizard()
            return redirect(reverse("espace_referent:aidant_new_profile"))
        return None

    def get(self, request, *args, **kwargs):
        redirect_response = self._guard_profile_or_redirect()
        if redirect_response:
            return redirect_response
        return self._no_cache_response(super().get(request, *args, **kwargs))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        formset = kwargs.get("formset")
        if formset is None:
            initial = self._build_trained_initial_from_session()
            formset = self._get_structure_change_formset(initial=initial)
        ctx["formset"] = formset
        return ctx

    def post(self, request, *args, **kwargs):
        redirect_response = self._guard_profile_or_redirect()
        if redirect_response:
            return redirect_response
        if request.POST.get("partial-add-trained"):
            data = request.POST.copy()
            empty_formset = self._get_structure_change_formset()
            prefix = empty_formset.prefix
            total = int(data.get(f"{prefix}-TOTAL_FORMS", 1))
            data[f"{prefix}-TOTAL_FORMS"] = str(total + 1)
            formset = self._get_structure_change_formset(data=data)
            return self.render_to_response(self.get_context_data(formset=formset))

        formset = self._get_structure_change_formset(data=request.POST)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(formset=formset))

        needs_lookup_display = any(
            f.cleaned_data
            and f.cleaned_data.get("email")
            and not f.cleaned_data.get("email_lookup_done")
            and f.email_lookup_case
            in (
                StructureChangeRequestForm.EMAIL_LOOKUP_REFERENT_OF_OTHER_ORG,
                StructureChangeRequestForm.EMAIL_LOOKUP_OTHER_ORG,
            )
            for f in formset.forms
        )
        if needs_lookup_display:
            return self.render_to_response(self.get_context_data(formset=formset))

        structure_data = []
        for f in formset.forms:
            if not f.cleaned_data or not f.cleaned_data.get("email"):
                continue
            structure_data.append(
                {
                    "email": f.cleaned_data["email"],
                    "new_email": f.cleaned_data.get("new_email"),
                    "email_lookup_case": f.email_lookup_case,
                }
            )
        if not structure_data:
            formset.non_form_errors().append(
                "Vous devez renseigner au moins un aidant."
            )
            return self.render_to_response(self.get_context_data(formset=formset))

        self._save_wizard(structure_change_data=structure_data)
        self._save_wizard(ready_for_confirmation=True)
        return redirect(reverse("espace_referent:aidant_new_confirmation"))


@method_decorator(activity_required, name="get")
@responsable_logged_required
class AddAidantUntrainedView(AddAidantWizardMixin, FormView):
    """Step 2b: enter untrained aidants (classic habilitation request form)."""

    template_name = (
        "aidants_connect_web/espace_responsable/add-aidant-wizard-step2-untrained.html"
    )
    form_class = NewHabilitationRequestForm

    def _wizard_step(self):
        return 2

    def _back_url(self):
        return reverse("espace_referent:aidant_new_profile")

    def get(self, request, *args, **kwargs):
        if self._profile_choice() != AddAidantProfileChoice.NOT_YET_TRAINED:
            self._clear_wizard()
            return redirect(reverse("espace_referent:aidant_new_profile"))
        return self._no_cache_response(super().get(request, *args, **kwargs))

    def _build_untrained_initial_from_session(self):
        """Build form initial dict from session classic_data for back navigation."""
        classic = self._wizard.get("classic_data")
        if not classic:
            return None
        course_type = classic.get("course_type") or {}
        hab_list = classic.get("habilitation_requests") or []
        org_ids = set(self.referent.responsable_de.values_list("pk", flat=True))
        # Default org for empty/invalid slots so we preserve form count
        default_org = (
            self.referent.responsable_de.first()
            if self.referent.responsable_de.exists()
            else None
        )
        hab_initial = []
        for h in hab_list:
            org_id = h.get("organisation_id")
            if org_id is not None:
                try:
                    org_id = int(org_id)
                except (TypeError, ValueError):
                    org_id = None
            if org_id is not None and org_id in org_ids:
                try:
                    org = Organisation.objects.get(pk=org_id)
                except (Organisation.DoesNotExist, ValueError):
                    org = default_org
            else:
                org = default_org
            if org is None:
                continue
            conseiller_numerique = h.get("conseiller_numerique", False)
            if isinstance(conseiller_numerique, str):
                conseiller_numerique = conseiller_numerique in ("True", "true", "1")
            else:
                conseiller_numerique = bool(conseiller_numerique)
            hab_initial.append(
                {
                    "email": h.get("email") or "",
                    "first_name": h.get("first_name") or "",
                    "last_name": h.get("last_name") or "",
                    "profession": h.get("profession") or "",
                    "organisation": org,
                    "conseiller_numerique": conseiller_numerique,
                }
            )
        return {
            "course_type": {
                "type": course_type.get("type"),
                "email_formateur": course_type.get("email_formateur") or "",
            },
            "habilitation_requests": hab_initial,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self._new_habilitation_form_kwargs())
        # Only pass initial on GET (unbound form) to pre-fill fields.
        # On POST, passing initial causes has_changed()=False for unchanged
        # extra forms, making Django reset cleaned_data to {}.
        if self.request.method == "GET":
            initial = self._build_untrained_initial_from_session()
            if initial is not None:
                kwargs["initial"] = initial
        return kwargs

    def post(self, request, *args, **kwargs):
        if self._profile_choice() != AddAidantProfileChoice.NOT_YET_TRAINED:
            self._clear_wizard()
            return redirect(reverse("espace_referent:aidant_new_profile"))
        if "partial-submit" in request.POST:
            data = request.POST.copy()
            total_forms = int(
                data.get("multiform-habilitation_requests-TOTAL_FORMS", 0)
            )
            form = NewHabilitationRequestForm(
                data=data, **self._new_habilitation_form_kwargs()
            )
            is_valid = form.is_valid()
            has_email_errors = False
            if "habilitation_requests" in form.forms:
                has_email_errors = any(
                    "email" in f.errors for f in form["habilitation_requests"].forms
                )
            if is_valid and not has_email_errors:
                data["multiform-habilitation_requests-TOTAL_FORMS"] = str(
                    total_forms + 1
                )
                form = NewHabilitationRequestForm(
                    data=data, **self._new_habilitation_form_kwargs()
                )
                form.is_valid()
            return self.render_to_response(
                self.get_context_data(form=form, is_partial_submit=True)
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        classic_data = self._serialize_classic_data(form.cleaned_data)
        self._save_wizard(classic_data=classic_data, ready_for_confirmation=True)
        return redirect(reverse("espace_referent:aidant_new_confirmation"))


@method_decorator(activity_required, name="get")
@responsable_logged_required
class AddAidantConfirmationView(AddAidantWizardMixin, TemplateView):
    """Final step: review and confirm, then create objects in DB."""

    template_name = (
        "aidants_connect_web/espace_responsable/add-aidant-wizard-confirmation.html"
    )
    success_url = reverse_lazy("espace_referent:aidants")

    def _wizard_step(self):
        return 3

    def get(self, request, *args, **kwargs):
        if not self._is_ready_for_confirmation():
            self._clear_wizard()
            return redirect(reverse("espace_referent:aidant_new_profile"))
        return self._no_cache_response(super().get(request, *args, **kwargs))

    def _back_url(self):
        profile = self._profile_choice()
        if profile == AddAidantProfileChoice.NOT_YET_TRAINED:
            return reverse("espace_referent:aidant_new_untrained")
        return reverse("espace_referent:aidant_new_trained")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        classic = self._wizard.get("classic_data") or {}
        ctx["course_type"] = classic.get("course_type") or {}
        ctx["AddAidantProfileChoice"] = AddAidantProfileChoice
        ctx["HabilitationRequestCourseType"] = HabilitationRequestCourseType

        structure_data = self._wizard.get("structure_change_data") or []
        ctx["direct_adds"] = [
            item
            for item in structure_data
            if item.get("email_lookup_case")
            == StructureChangeRequestForm.EMAIL_LOOKUP_REFERENT_OF_OTHER_ORG
        ]
        ctx["structure_requests"] = [
            item
            for item in structure_data
            if item.get("email_lookup_case")
            == StructureChangeRequestForm.EMAIL_LOOKUP_OTHER_ORG
        ]
        return ctx

    def post(self, request, *args, **kwargs):
        if not self._is_ready_for_confirmation():
            self._clear_wizard()
            return redirect(reverse("espace_referent:aidant_new_profile"))
        if not request.POST.get("wizard_confirm"):
            return redirect(reverse("espace_referent:aidant_new_confirmation"))

        profile = self._profile_choice()
        classic = self._wizard.get("classic_data")
        structure_data = self._wizard.get("structure_change_data") or []

        with transaction.atomic():
            if profile == AddAidantProfileChoice.NOT_YET_TRAINED:
                if classic:
                    self._create_classic_requests(classic)

            if profile == AddAidantProfileChoice.ALREADY_TRAINED:
                target_org = self.referent.organisation

                for item in structure_data:
                    aidant = Aidant.objects.filter(
                        username__iexact=item["email"]
                    ).first()
                    if not aidant:
                        continue

                    lookup_case = item.get("email_lookup_case")

                    if (
                        lookup_case
                        == StructureChangeRequestForm.EMAIL_LOOKUP_REFERENT_OF_OTHER_ORG
                    ):
                        # Case 1: referent manages the aidant's current org
                        # → move directly without creating a request.
                        aidant.organisations.add(target_org)
                    else:
                        # Case 2: create a StructureChangeRequest for review.
                        scr = StructureChangeRequest.objects.create(
                            aidant=aidant,
                            email=item["email"],
                            organisation_id=target_org.pk,
                            new_email=item.get("new_email"),
                        )
                        previous_ids = list(
                            aidant.organisations.exclude(pk=target_org.pk).values_list(
                                "pk", flat=True
                            )
                        )
                        scr.previous_organisations.set(previous_ids)

        self._clear_wizard()

        django_messages.success(
            self.request,
            "Votre ou vos demande(s) ont été enregistrées avec succès.",
        )
        return redirect(self.success_url)


@responsable_logged_with_activity_required
class CancelHabilitationRequestView(DetailView):
    pk_url_kwarg = "request_id"
    model = HabilitationRequest
    context_object_name = "request"
    template_name = (
        "aidants_connect_web/espace_responsable/cancel-habilitation-request.html"
    )

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        referent_organisation_ids = self.aidant.responsable_de.values_list(
            "id", flat=True
        )
        return (
            super()
            .get_queryset()
            .filter(
                organisation__in=referent_organisation_ids,
                status__in=ReferentRequestStatuses.cancellable_by_responsable(),
            )
        )

    def post(self, request, *args, **kwargs):
        self.get_object().cancel_by_responsable()
        return redirect(reverse("espace_referent:aidants"))


@responsable_logged_with_activity_required
class CancelStructureChangeRequestView(DetailView):
    pk_url_kwarg = "request_id"
    model = StructureChangeRequest
    context_object_name = "request"
    template_name = (
        "aidants_connect_web/espace_responsable/cancel-structure-change-request.html"
    )

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        referent_organisation_ids = self.aidant.responsable_de.values_list(
            "id", flat=True
        )
        return (
            super()
            .get_queryset()
            .filter(
                organisation__in=referent_organisation_ids,
                status__in=StructureChangeRequestStatuses.cancellable_by_responsable(),
            )
        )

    def post(self, request, *args, **kwargs):
        self.get_object().cancel_by_responsable()
        return redirect(reverse("espace_referent:aidants"))


@responsable_logged_with_activity_required
class FormationRegistrationView(CommonFormationRegistrationView):
    success_url = reverse_lazy("espace_referent:aidants")

    def get_habilitation_request(self) -> HabilitationRequest:
        return get_object_or_404(
            HabilitationRequest,
            pk=self.kwargs["request_id"],
            organisation=self.request.user.organisation,
        )

    def get_cancel_url(self) -> str:
        return reverse("espace_referent:aidants")
