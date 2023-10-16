import base64
import logging
from gettext import ngettext as _
from io import BytesIO

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DeleteView, DetailView, FormView, TemplateView

import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_common.utils.constants import RequestStatusConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_web.constants import (
    OTP_APP_DEVICE_NAME,
    HabilitationRequestStatuses,
    NotificationType,
)
from aidants_connect_web.decorators import (
    responsable_logged_with_activity_required,
    user_is_responsable_structure,
)
from aidants_connect_web.forms import (
    AddAppOTPToAidantForm,
    AddOrganisationResponsableForm,
    CarteOTPSerialNumberForm,
    CarteTOTPValidationForm,
    ChangeAidantOrganisationsForm,
    HabilitationRequestCreationForm,
    RemoveCardFromAidantForm,
)
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    HabilitationRequest,
    Journal,
    Notification,
    Organisation,
)

logger = logging.getLogger()


@method_decorator([login_required, user_is_responsable_structure], name="dispatch")
class Home(TemplateView):
    template_name = "aidants_connect_web/espace_responsable/home.html"

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.organisations = (
            Organisation.objects.filter(responsables=self.referent)
            .prefetch_related("current_aidants")
            .order_by("name")
        )

        if self.organisations.count() == 1:
            return redirect(
                "espace_responsable_organisation",
                organisation_id=self.organisations[0].id,
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "responsable": self.referent,
            "organisations": self.organisations,
        }


@responsable_logged_with_activity_required
class OrganisationView(DetailView):
    template_name = "aidants_connect_web/espace_responsable/organisation.html"
    pk_url_kwarg = "organisation_id"
    context_object_name = "organisation"
    model = Organisation

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(responsables=self.referent)

    def get_context_data(self, **kwargs):
        referents_qs = (
            self.object.responsables.exclude(pk=self.referent.pk)
            .order_by("last_name")
            .prefetch_related("carte_totp")
        )
        organisation_active_referents = [
            self.referent,
            *referents_qs.filter(is_active=True),
        ]
        organisation_inactive_referents = referents_qs.filter(is_active=False)

        aidantq_qs = self.object.aidants_not_responsables.order_by(
            "last_name"
        ).prefetch_related("carte_totp")

        organisation_active_aidants = aidantq_qs.filter(is_active=True)
        organisation_inactive_aidants = aidantq_qs.filter(is_active=False)

        organisation_habilitation_requests = self.object.habilitation_requests.exclude(
            status=HabilitationRequestStatuses.STATUS_VALIDATED.value
        ).order_by("status", "last_name")

        return {
            **super().get_context_data(**kwargs),
            "referent": self.referent,
            "referent_notifications": Notification.objects.get_displayable_for_user(
                self.referent
            ),
            "notification_type": NotificationType,
            "organisation_active_referents": organisation_active_referents,
            "organisation_inactive_referents": organisation_inactive_referents,
            "organisation_active_aidants": organisation_active_aidants,
            "organisation_inactive_aidants": organisation_inactive_aidants,
            "organisation_habilitation_requests": organisation_habilitation_requests,
            "FF_OTP_APP": settings.FF_OTP_APP and self.referent.ff_otp_app,
        }


@responsable_logged_with_activity_required
class OrganisationResponsables(FormView):
    form_class = AddOrganisationResponsableForm
    template_name = "aidants_connect_web/espace_responsable/responsables.html"

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.organisation = get_object_or_404(
            Organisation, pk=kwargs.get("organisation_id"), responsables=self.referent
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "organisation": self.organisation}

    def form_valid(self, form):
        new_responsable = form.cleaned_data["candidate"]
        new_responsable.responsable_de.add(self.organisation)
        new_responsable.save()
        django_messages.success(
            self.request,
            (
                f"Tout s’est bien passé, {new_responsable} est maintenant responsable"
                f"de l’organisation {self.organisation}."
            ),
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "espace_responsable_organisation",
            kwargs={"organisation_id": self.organisation.pk},
        )

    def get_context_data(self, **kwargs):
        kwargs.update({"user": self.referent, "organisation": self.organisation})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class AidantView(TemplateView):
    template_name = "aidants_connect_web/espace_responsable/aidant.html"

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.aidant = get_object_or_404(Aidant, pk=kwargs.get("aidant_id"))
        if not self.referent.can_see_aidant(self.aidant):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "aidant": self.aidant,
                "responsable": self.referent,
                "form": ChangeAidantOrganisationsForm(self.referent, self.aidant),
            }
        )
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class RemoveCardFromAidant(FormView):
    template_name = "aidants_connect_web/espace_responsable/aidant_remove_card.html"
    form_class = RemoveCardFromAidantForm
    success_url = reverse_lazy("espace_responsable_home")

    def dispatch(self, request, *args, **kwargs):
        self.responsable: Aidant = request.user
        self.aidant: Aidant = get_object_or_404(Aidant, pk=kwargs.get("aidant_id"))

        if not self.responsable.can_see_aidant(self.aidant):
            raise Http404

        if not self.aidant.has_a_carte_totp:
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "responsable": self.responsable,
        }

    def form_valid(self, form):
        sn = self.aidant.carte_totp.serial_number

        carte = CarteTOTP.objects.get(serial_number=sn)

        with transaction.atomic():
            carte.unlink_aidant()

            Journal.log_card_dissociation(
                self.responsable, self.aidant, sn, form.cleaned_data["reason"]
            )

        django_messages.success(
            self.request,
            (
                f"Tout s’est bien passé, la carte {sn} a été séparée du compte "
                f"de l’aidant {self.aidant.get_full_name()}."
            ),
        )

        return super().form_valid(form)


@responsable_logged_with_activity_required
class AddAppOTPToAidant(FormView):
    template_name = "aidants_connect_web/espace_responsable/app_otp_confirm.html"
    form_class = AddAppOTPToAidantForm
    success_url = reverse_lazy("espace_responsable_home")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user

        if not settings.FF_OTP_APP or not self.referent.ff_otp_app:
            return HttpResponseRedirect(reverse("espace_responsable_home"))

        self.aidant: Aidant = get_object_or_404(Aidant, pk=kwargs["aidant_id"])

        if not self.referent.can_see_aidant(self.aidant):
            raise Http404()

        if self.aidant.has_otp_app:
            django_messages.warning(
                request,
                "Il existe déjà une carte OTP numérique liée à ce profil. "
                "Si vous voulez en attacher une nouvelle, veuillez supprimer "
                "l’anciennne.",
            )
            return HttpResponseRedirect(self.get_success_url())

        if not self.aidant.is_active:
            django_messages.warning(
                request,
                f"Le profil de {self.aidant.get_full_name()} désactivé. "
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
class RemoveAppOTPFromAidant(DeleteView):
    template_name = "aidants_connect_web/espace_responsable/app_otp_remove.html"
    success_url = reverse_lazy("espace_responsable_home")

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        self.aidant: Aidant = get_object_or_404(Aidant, pk=kwargs["aidant_id"])

        if not self.referent.can_see_aidant(self.aidant):
            raise Http404()

        if (
            not self.aidant.has_otp_app
            or not settings.FF_OTP_APP
            or not self.referent.ff_otp_app
        ):
            return HttpResponseRedirect(reverse("espace_responsable_home"))

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
class RemoveAidantFromOrganisationView(TemplateView):
    template_name = "aidants_connect_web/espace_responsable/confirm-remove-aidant-from-organisation.html"  # noqa: E501

    def dispatch(self, request, aidant_id: int, organisation_id: int, *args, **kwargs):
        self.referent: Aidant = request.user
        self.aidant: Aidant = get_object_or_404(Aidant, pk=aidant_id)
        self.organisation: Organisation = get_object_or_404(
            Organisation, pk=organisation_id
        )

        if not self.referent.can_see_aidant(self.aidant):
            raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        result = self.aidant.remove_from_organisation(self.organisation)
        if result is True:
            django_messages.success(
                request,
                f"{self.aidant.get_full_name()} ne fait maintenant plus partie de "
                f"{self.organisation.name}.",
            )
        else:
            django_messages.success(
                request, f"Le profil de {self.aidant.get_full_name()} a été désactivé."
            )

        return redirect(
            "espace_responsable_organisation", organisation_id=self.organisation.id
        )

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant, "organisation": self.organisation})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class ChangeAidantOrganisations(FormView):
    form_class = ChangeAidantOrganisationsForm

    def dispatch(self, request, aidant_id: int, *args, **kwargs):
        self.responsable: Aidant = request.user
        self.aidant = get_object_or_404(Aidant, pk=aidant_id)
        if not self.responsable.can_see_aidant(self.aidant):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # GET is not used
        return self.http_method_not_allowed(request, *args, **kwargs)

    def form_invalid(self, form):
        django_messages.error(self.request, str(form.errors["organisations"]))
        return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

    def form_valid(self, form):
        responsable_organisations = self.responsable.responsable_de.all()
        aidant_organisations = self.aidant.organisations.all()
        posted_organisations = form.cleaned_data["organisations"]

        unrelated_organisations = aidant_organisations.difference(
            responsable_organisations
        )
        self.aidant.set_organisations(
            unrelated_organisations.union(posted_organisations)
        )

        message = _(
            "Tout s’est bien passé, le compte de %(u)s "
            "a été rattaché aux organisations %(org)s",
            "Tout s’est bien passé, le compte de %(u)s "
            "a été rattaché aux organisations %(org)s",
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
            "responsable": self.responsable,
            "aidant": self.aidant,
        }

    def get_success_url(self):
        return reverse(
            "espace_responsable_aidant", kwargs={"aidant_id": self.aidant.id}
        )


@responsable_logged_with_activity_required
class ChooseTOTPDevice(TemplateView):
    template_name = "aidants_connect_web/espace_responsable/choose-totp-device.html"

    def dispatch(self, request, aidant_id: int, *args, **kwargs):
        self.referent: Aidant = request.user
        self.aidant = get_object_or_404(Aidant, pk=aidant_id)
        if not self.referent.can_see_aidant(self.aidant):
            raise Http404

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

        can_use_digital_option = settings.FF_OTP_APP and self.referent.ff_otp_app
        digital_option_available = (
            self.aidant.has_otp_app or self.aidant.is_active and can_use_digital_option
        )
        digital_option_unavailable_text = (
            option_unavailable_text % "numérique"
            if can_use_digital_option
            else "Cette option est désactivée pour vous actuellement"
        )

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
class AssociateAidantCarteTOTP(FormView):
    form_class = CarteOTPSerialNumberForm
    template_name = "aidants_connect_web/espace_responsable/write-carte-totp-sn.html"

    def dispatch(self, request, aidant_id: int, *args, **kwargs):
        self.responsable: Aidant = request.user
        self.aidant = get_object_or_404(Aidant, pk=aidant_id)
        if not self.responsable.can_see_aidant(self.aidant):
            raise Http404

        if self.aidant.has_a_carte_totp:
            django_messages.error(
                request,
                (
                    f"Le compte de {self.aidant.get_full_name()} est déjà lié à une "
                    f"carte Aidants Connect. Vous devez d’abord retirer la carte de "
                    f"son compte avant de pouvoir en lier une nouvelle."
                ),
            )

            return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

        if not self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"Le compte de {self.aidant.get_full_name()} est désactivé. "
                    "Il est impossible de lui attacher une nouvelle carte "
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
                Journal.log_card_association(
                    self.responsable, self.aidant, serial_number
                )

            from aidants_connect_web.signals import card_associated_to_aidant

            card_associated_to_aidant.send(None, otp_device=carte_totp.totp_device)

        except Exception:
            message = "Une erreur s’est produite lors de la sauvegarde de la carte."
            logger.exception(message)
            django_messages.error(self.request, message)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant, "responsable": self.responsable})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class ValidateAidantCarteTOTP(FormView):
    form_class = CarteTOTPValidationForm
    template_name = "aidants_connect_web/espace_responsable/validate-carte-totp.html"

    def dispatch(self, request, aidant_id: int, *args, **kwargs):
        self.responsable: Aidant = request.user
        self.aidant = get_object_or_404(Aidant, pk=aidant_id)
        if not self.responsable.can_see_aidant(self.aidant):
            raise Http404

        if not self.aidant.has_a_carte_totp:
            django_messages.error(
                request,
                (
                    "Impossible de trouver une carte Aidants Connect associée au "
                    f"compte de {self.aidant.get_full_name()}."
                    "Vous devez d’abord lier une carte à son compte."
                ),
            )

            return redirect("espace_responsable_aidant", aidant_id=self.aidant.id)

        if not self.aidant.is_active:
            django_messages.error(
                request,
                (
                    f"Le profil de {self.aidant.get_full_name()} est désactivé. "
                    "Il est impossible de valider la carte Aidants Connect qui lui est "
                    "associée."
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
                self.responsable, self.aidant, self.aidant.carte_totp.serial_number
            )
            # check if the validation request is for the référent
            if self.responsable.pk == self.aidant.pk:
                # get all organisations aidant is référent
                valid_organisation_requests = OrganisationRequest.objects.filter(
                    organisation__in=self.responsable.responsable_de.all()
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
            (
                "Tout s’est bien passé, le compte de "
                f"{self.aidant.get_full_name()} est prêt !"
            ),
        )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({"aidant": self.aidant})
        return super().get_context_data(**kwargs)


@responsable_logged_with_activity_required
class NewHabilitationRequest(FormView):
    template_name = (
        "aidants_connect_web/espace_responsable/new-habilitation-request.html"
    )
    form_class = HabilitationRequestCreationForm

    def dispatch(self, request, *args, **kwargs):
        self.referent: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "referent": self.referent}

    def get_success_url(self):
        return reverse(
            "espace_responsable_organisation",
            kwargs={"organisation_id": self.habilitation_request.organisation.id},
        )

    def form_valid(self, form):
        self.habilitation_request = form.save(commit=False)

        if Aidant.objects.filter(
            email__iexact=self.habilitation_request.email,
            organisation__in=self.referent.responsable_de.all(),
        ).exists():
            form.add_error(
                "email",
                "Il existe déjà un compte aidant pour cette adresse e-mail. "
                "Vous n’avez pas besoin de déposer une "
                "nouvelle demande pour cette adresse-ci.",
            )
            return super().form_invalid(form)

        if HabilitationRequest.objects.filter(
            email=self.habilitation_request.email,
            organisation__in=self.referent.responsable_de.all(),
        ).exists():
            form.add_error(
                "email",
                "Une demande d’habilitation est déjà en cours pour l’adresse e-mail. "
                "Vous n’avez pas besoin de déposer une "
                "nouvelle demande pour cette adresse-ci.",
            )
            return super().form_invalid(form)

        self.habilitation_request.origin = HabilitationRequest.ORIGIN_RESPONSABLE
        self.habilitation_request.save()
        django_messages.success(
            self.request,
            (
                f"La requête d’habilitation pour "
                f"{self.habilitation_request.first_name} "
                f"{self.habilitation_request.last_name} a bien été enregistrée."
            ),
        )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)


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
                status__in=HabilitationRequestStatuses.cancellable_by_responsable(),
            )
        )

    def post(self, request, *args, **kwargs):
        self.get_object().cancel_by_responsable()
        return redirect(reverse("espace_responsable_home"))
