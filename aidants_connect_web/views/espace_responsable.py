import base64
import logging
from gettext import ngettext as _
from io import BytesIO
from itertools import chain

from django.contrib import messages as django_messages
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ngettext
from django.views.generic import DeleteView, DetailView, FormView, TemplateView

import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.views import (
    FormationRegistrationView as CommonFormationRegistrationView,
)
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_web.constants import (
    OTP_APP_DEVICE_NAME,
    NotificationType,
    ReferentRequestStatuses,
)
from aidants_connect_web.decorators import (
    activity_required,
    responsable_logged_required,
    responsable_logged_with_activity_required,
)
from aidants_connect_web.forms import (
    AddAppOTPToAidantForm,
    AddOrganisationReferentForm,
    CarteOTPSerialNumberForm,
    CarteTOTPValidationForm,
    ChangeAidantOrganisationsForm,
    CoReferentNonAidantRequestForm,
    NewHabilitationRequestForm,
    OrganisationRestrictDemarchesForm,
    RemoveCardFromAidantForm,
)
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    CoReferentNonAidantRequest,
    HabilitationRequest,
    Journal,
    Notification,
    Organisation,
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
        return redirect("espace_responsable_organisation")


@responsable_logged_required
# We don't want to check activity on POST route
@responsable_logged_with_activity_required(method_name="get")
class OrganisationView(DetailView, FormView):
    template_name = "aidants_connect_web/espace_responsable/organisation.html"
    context_object_name = "organisation"
    model = Organisation
    form_class = OrganisationRestrictDemarchesForm
    success_url = reverse_lazy("espace_responsable_organisation")

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
    success_url = reverse_lazy("espace_responsable_organisation")

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
    success_url = reverse_lazy("espace_responsable_referents")

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
            return redirect("espace_aidant_home")
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
    success_url = reverse_lazy("espace_responsable_aidants")

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
            return redirect("espace_aidant_home")
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
class DemandesView(DetailView, FormView):
    template_name = "aidants_connect_web/espace_responsable/demandes.html"
    context_object_name = "organisation"
    model = Organisation
    form_class = OrganisationRestrictDemarchesForm
    success_url = reverse_lazy("espace_responsable_demandes")

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
            return redirect("espace_aidant_home")
        return self.organisation

    def get_context_data(self, **kwargs):
        organisation_habilitation_requests = self.object.habilitation_requests.filter(
            status__in=[
                ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
                ReferentRequestStatuses.STATUS_NEW.value,
            ],
            created_by_fne=False,
        ).order_by("status", "last_name")
        organisation_habilitation_validated = self.object.habilitation_requests.filter(
            status__in=[
                ReferentRequestStatuses.STATUS_PROCESSING.value,
                ReferentRequestStatuses.STATUS_PROCESSING_P2P.value,
            ],
            created_by_fne=False,
        ).order_by("status", "last_name")
        organisation_habilitation_refused = self.object.habilitation_requests.filter(
            status__in=[
                ReferentRequestStatuses.STATUS_REFUSED.value,
                ReferentRequestStatuses.STATUS_CANCELLED.value,
                ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE.value,
            ],
            created_by_fne=False,
        ).order_by("status", "last_name")

        return {
            **super().get_context_data(**kwargs),
            "notification_type": NotificationType,
            "organisation_habilitation_requests": organisation_habilitation_requests,
            "organisation_habilitation_validated": organisation_habilitation_validated,
            "organisation_habilitation_refused": organisation_habilitation_refused,
            "perimetres_form": super().get_form(),
        }


@responsable_logged_with_activity_required
class OrganisationResponsables(FormView):
    template_name = "aidants_connect_web/espace_responsable/responsables.html"
    success_url = reverse_lazy("espace_responsable_referents")

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
class RemoveCardFromAidant(ReferentCannotManageAidantResponseMixin, FormView):
    template_name = "aidants_connect_web/espace_responsable/aidant_remove_card.html"
    form_class = RemoveCardFromAidantForm
    success_url = reverse_lazy("espace_responsable_aidants")

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
    success_url = reverse_lazy("espace_responsable_organisation")

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
    success_url = reverse_lazy("espace_responsable_organisation")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        if not self.referent.can_manage_aidant(kwargs["aidant_id"]):
            return self.referent_cannot_manage_aidant_response()

        self.aidant: Aidant = Aidant.objects.get(pk=kwargs["aidant_id"])

        if not self.aidant.has_otp_app:
            return HttpResponseRedirect(reverse("espace_responsable_organisation"))

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
            return redirect("espace_responsable_referents")
        else:
            return redirect("espace_responsable_aidants")

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
            return redirect("espace_responsable_referents")
        else:
            return redirect("espace_responsable_aidants")

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant, "organisation": self.organisation})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class ChangeAidantOrganisations(ReferentCannotManageAidantResponseMixin, FormView):
    form_class = ChangeAidantOrganisationsForm
    success_url = reverse_lazy("espace_responsable_organisation")

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
        return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

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

            return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

        if not self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"Erreur : le compte de {self.aidant.get_full_name()} est désactivé"
                    ". Il est impossible de lui attacher une nouvelle carte "
                    "Aidant Connect"
                ),
            )

            return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "espace_responsable_validate_totp", kwargs={"aidant_id": self.aidant.id}
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

            return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

        if not self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"Erreur : le profil de {self.aidant.get_full_name()} est désactivé"
                    ". Il est impossible de valider la carte Aidants Connect "
                    "qui lui est associée."
                ),
            )

            return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "espace_responsable_aidant", kwargs={"aidant_id": self.aidant.id}
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


@method_decorator(activity_required, name="get")
@responsable_logged_required
class NewHabilitationRequest(FormView):
    template_name = "aidants_connect_web/espace_responsable/new-habilitation-request.html"  # noqa: E501
    form_class = NewHabilitationRequestForm
    success_url = reverse_lazy("espace_responsable_aidants")

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.referent: Aidant = request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "form_kwargs": {
                    "habilitation_requests": {
                        "form_kwargs": {"referent": self.referent}
                    }
                }
            }
        )

        return kwargs

    def get_form_kwargs_with_data(self, data):
        """Helper method to get form kwargs with custom data"""
        kwargs = self.get_form_kwargs()
        kwargs["data"] = data
        return kwargs

    def post(self, request, *args, **kwargs):
        if "partial-submit" in request.POST:
            data = request.POST.copy()
            total_forms = int(
                data.get("multiform-habilitation_requests-TOTAL_FORMS", 0)
            )

            # First validate the current form without adding a new one
            form = self.get_form_class()(**self.get_form_kwargs_with_data(data))
            is_valid = form.is_valid()

            # Check specifically for email validation errors
            has_email_errors = False
            if hasattr(form, "forms") and "habilitation_requests" in form.forms:
                habilitation_formset = form["habilitation_requests"]
                for subform in habilitation_formset.forms:
                    if "email" in subform.errors:
                        has_email_errors = True
                        break

            # Only add a new form if validation passes AND there are no email errors
            if is_valid and not has_email_errors:
                data["multiform-habilitation_requests-TOTAL_FORMS"] = str(
                    total_forms + 1
                )
                form = self.get_form_class()(**self.get_form_kwargs_with_data(data))
                form.is_valid()  # Trigger validation for the new form structure

            return self.render_to_response(
                self.get_context_data(form=form, is_partial_submit=True)
            )

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        result: list[HabilitationRequest] = form.save()["habilitation_requests"]
        django_messages.success(
            self.request,
            ngettext(
                (
                    "La demande d'habilitation pour %(person)s "
                    "a été enregistrée avec succès."
                ),
                (
                    "Les %(len)s demandes d'habilitation ont été "
                    "enregistrées avec succès."
                ),
                len(result),
            )
            % {"person": result[0].get_full_name(), "len": len(result)},
        )
        return super().form_valid(form)


@responsable_logged_with_activity_required
class CancelHabilitationRequestView(DetailView):
    pk_url_kwarg = "request_id"
    model = HabilitationRequest
    context_object_name = "request"
    template_name = "aidants_connect_web/espace_responsable/cancel-habilitation-request.html"  # noqa: E501

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        org_ids = self.aidant.responsable_de.values_list("id", flat=True)
        return (
            super()
            .get_queryset()
            .filter(
                organisation__in=org_ids,
                status__in=ReferentRequestStatuses.cancellable_by_responsable(),
            )
        )

    def post(self, request, *args, **kwargs):
        self.get_object().cancel_by_responsable()
        return redirect(reverse("espace_responsable_organisation"))


@responsable_logged_with_activity_required
class FormationRegistrationView(CommonFormationRegistrationView):
    success_url = reverse_lazy("espace_responsable_aidants")

    def get_habilitation_request(self) -> HabilitationRequest:
        return get_object_or_404(
            HabilitationRequest,
            pk=self.kwargs["request_id"],
            organisation=self.request.user.organisation,
        )

    def get_cancel_url(self) -> str:
        return reverse("espace_responsable_demandes")
