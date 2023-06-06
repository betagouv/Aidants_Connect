import base64
import contextlib
from io import BytesIO

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic import DeleteView, FormView, TemplateView

import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_common.utils.constants import RequestStatusConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_web.decorators import (
    activity_required,
    aidant_logged_with_activity_required,
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
    Organisation,
)


def check_organisation_and_responsable(responsable: Aidant, organisation: Organisation):
    if responsable not in organisation.responsables.all():
        raise Http404


@require_GET
@login_required
@user_is_responsable_structure
def home(request):
    responsable = request.user
    organisations = (
        Organisation.objects.filter(responsables=responsable)
        .prefetch_related("current_aidants")
        .order_by("name")
    )

    if organisations.count() == 1:
        organisation = organisations[0]
        return redirect(
            "espace_responsable_organisation", organisation_id=organisation.id
        )

    return render(
        request,
        "aidants_connect_web/espace_responsable/home.html",
        {"responsable": responsable, "organisations": organisations},
    )


@method_decorator(
    [login_required, user_is_responsable_structure, activity_required], name="dispatch"
)
class OrganisationView(TemplateView):
    template_name = "aidants_connect_web/espace_responsable/organisation.html"

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        self.organisation: Organisation = get_object_or_404(
            Organisation, pk=kwargs.get("organisation_id")
        )

        check_organisation_and_responsable(self.aidant, self.organisation)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        organisation_active_aidants = [
            self.aidant,
            *(
                self.organisation.responsables.exclude(pk=self.aidant.pk)
                .order_by("last_name")
                .prefetch_related("carte_totp")
            ),
            *(
                self.organisation.aidants_not_responsables.filter(is_active=True)
                .order_by("last_name")
                .prefetch_related("carte_totp")
            ),
        ]

        organisation_habilitation_requests = (
            self.organisation.habilitation_requests.exclude(
                status=HabilitationRequest.STATUS_VALIDATED
            ).order_by("status", "last_name")
        )

        organisation_inactive_aidants = (
            self.organisation.aidants_not_responsables.filter(is_active=False)
            .order_by("last_name")
            .prefetch_related("carte_totp")
        )

        return {
            **super().get_context_data(**kwargs),
            "responsable": self.aidant,
            "responsables": list(
                self.organisation.responsables.values_list("pk", flat=True)
            ),
            "organisation": self.organisation,
            "organisation_active_aidants": organisation_active_aidants,
            "organisation_habilitation_requests": organisation_habilitation_requests,
            "organisation_inactive_aidants": organisation_inactive_aidants,
        }


@require_http_methods(["GET", "POST"])
@login_required
@user_is_responsable_structure
@activity_required
def organisation_responsables(request, organisation_id):
    responsable: Aidant = request.user
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    check_organisation_and_responsable(responsable, organisation)

    if request.method == "GET":
        form = AddOrganisationResponsableForm(organisation)
        return render(
            request,
            "aidants_connect_web/espace_responsable/responsables.html",
            {
                "user": responsable,
                "organisation": organisation,
                "form": form,
            },
        )

    form = AddOrganisationResponsableForm(organisation, data=request.POST)
    if form.is_valid():
        data = form.cleaned_data
        new_responsable = data["candidate"]
        new_responsable.responsable_de.add(organisation)
        new_responsable.save()
        django_messages.success(
            request,
            (
                f"Tout s’est bien passé, {new_responsable} est maintenant responsable"
                f"de l’organisation {organisation}."
            ),
        )
        return redirect(
            "espace_responsable_organisation", organisation_id=organisation_id
        )
    return render(
        request,
        "aidants_connect_web/espace_responsable/responsables.html",
        {
            "user": responsable,
            "organisation": organisation,
            "form": form,
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
@user_is_responsable_structure
@activity_required
def aidant(request, aidant_id):
    responsable: Aidant = request.user
    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if not responsable.can_see_aidant(aidant):
        raise Http404

    form = RemoveCardFromAidantForm()
    orga_form = ChangeAidantOrganisationsForm(responsable, aidant)

    return render(
        request,
        "aidants_connect_web/espace_responsable/aidant.html",
        {
            "aidant": aidant,
            "form": form,
            "orga_form": orga_form,
            "responsable": responsable,
        },
    )


@aidant_logged_with_activity_required
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

        with transaction.atomic():
            carte = CarteTOTP.objects.get(serial_number=sn)

            with contextlib.suppress(TOTPDevice.DoesNotExist):
                TOTPDevice.objects.get(key=carte.seed, user=self.aidant).delete()

            carte.aidant = None
            carte.save()

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


@aidant_logged_with_activity_required
class AddAppOTPToAidant(FormView):
    template_name = "aidants_connect_web/espace_responsable/app_otp_confirm.html"
    form_class = AddAppOTPToAidantForm
    success_url = reverse_lazy("espace_responsable_home")

    def dispatch(self, request, *args, **kwargs):
        self.responsable: Aidant = request.user
        self.aidant: Aidant = get_object_or_404(Aidant, pk=kwargs["aidant_id"])

        if not self.responsable.can_see_aidant(self.aidant):
            raise Http404()

        if self.aidant.totpdevice_set.filter(
            name=TOTPDevice.APP_DEVICE_NAME % self.aidant.pk
        ).exists():
            django_messages.warning(
                request,
                "Il existe déjà une application OTP liée à ce profil. Si vous voulez "
                "en attacher une nouvelle, veuillez supprimer l'anciennne.",
            )
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.otp_device = TOTPDevice(
            user=self.aidant,
            name=TOTPDevice.APP_DEVICE_NAME % self.aidant.pk,
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
        self.otp_device.confirmed = True
        self.otp_device.save()
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


@aidant_logged_with_activity_required
class RemoveAppOTPFromAidant(DeleteView):
    template_name = "aidants_connect_web/espace_responsable/app_otp_remove.html"
    success_url = reverse_lazy("espace_responsable_home")

    def dispatch(self, request, *args, **kwargs):
        self.responsable: Aidant = request.user
        self.aidant: Aidant = get_object_or_404(Aidant, pk=kwargs["aidant_id"])

        if not self.responsable.can_see_aidant(self.aidant):
            raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "aidant": self.aidant}

    def get_object(self, queryset=None):
        return self.aidant.totpdevice_set.filter(
            name=TOTPDevice.APP_DEVICE_NAME % self.aidant.pk
        )


@require_http_methods(["GET", "POST"])
@login_required
@user_is_responsable_structure
@activity_required
def remove_aidant_from_organisation(
    request: HttpRequest, aidant_id: int, organisation_id: int
) -> HttpResponse:
    responsable: Aidant = request.user
    aidant: Aidant = get_object_or_404(Aidant, pk=aidant_id)
    organisation: Organisation = get_object_or_404(Organisation, pk=organisation_id)

    if not responsable.can_see_aidant(aidant):
        raise Http404()

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/espace_responsable/"
            "confirm-remove-aidant-from-organisation.html",
            {"aidant": aidant, "organisation": organisation},
        )

    result = aidant.remove_from_organisation(organisation)
    if result is True:
        django_messages.success(
            request,
            f"{aidant.get_full_name()} ne fait maintenant plus partie de "
            f"{organisation.name}.",
        )
    else:
        django_messages.success(
            request, f"Le profil de {aidant.get_full_name()} a été désactivé."
        )

    return redirect("espace_responsable_organisation", organisation_id=organisation.id)


@require_POST
@login_required
@user_is_responsable_structure
@activity_required
def change_aidant_organisations(request, aidant_id):
    responsable: Aidant = request.user
    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if not responsable.can_see_aidant(aidant):
        raise Http404

    form = ChangeAidantOrganisationsForm(responsable, aidant, data=request.POST)
    if not form.is_valid():
        errors = str(form.errors["organisations"])
        django_messages.error(request, errors)
        return redirect(
            "espace_responsable_aidant",
            aidant_id=aidant.id,
        )

    responsable_organisations = responsable.responsable_de.all()
    aidant_organisations = aidant.organisations.all()
    posted_organisations = form.cleaned_data["organisations"]

    unrelated_organisations = aidant_organisations.difference(responsable_organisations)
    aidant.set_organisations(unrelated_organisations.union(posted_organisations))

    if len(posted_organisations) > 1:
        message = (
            f"Tout s’est bien passé, {aidant} a été rattaché(e) aux organisations "
            f"{', '.join(org.name for org in posted_organisations)}."
        )
    else:
        message = (
            f"Tout s’est bien passé, {aidant} a été rattaché(e) à l'organisation "
            f"{posted_organisations[0].name}."
        )
    django_messages.success(request, message)

    return redirect(
        "espace_responsable_aidant",
        aidant_id=aidant.id,
    )


@require_http_methods(["GET", "POST"])
@login_required
@user_is_responsable_structure
@activity_required
def associate_aidant_carte_totp(request, aidant_id):
    responsable: Aidant = request.user
    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if not responsable.can_see_aidant(aidant):
        raise Http404

    if hasattr(aidant, "carte_totp"):
        django_messages.error(
            request,
            (
                f"Le compte de {aidant.get_full_name()} est déjà lié à une carte "
                "Aidants Connect. Vous devez d’abord retirer la carte de son compte "
                "avant de pouvoir en lier une nouvelle."
            ),
        )
        return redirect(
            "espace_responsable_aidant",
            aidant_id=aidant.id,
        )

    if request.method == "GET":
        form = CarteOTPSerialNumberForm()

    if request.method == "POST":
        form = CarteOTPSerialNumberForm(request.POST)
        if form.is_valid():
            serial_number = form.cleaned_data["serial_number"]
            try:
                carte_totp = CarteTOTP.objects.get(serial_number=serial_number)

                with transaction.atomic():
                    carte_totp.aidant = aidant
                    carte_totp.save()
                    totp_device = carte_totp.createTOTPDevice()
                    totp_device.save()
                    Journal.log_card_association(responsable, aidant, serial_number)

                return redirect(
                    "espace_responsable_validate_totp",
                    aidant_id=aidant.id,
                )
            except Exception:
                django_messages.error(
                    request,
                    "Une erreur s’est produite lors de la sauvegarde de la carte.",
                )
                # todo send exception to Sentry

    return render(
        request,
        "aidants_connect_web/espace_responsable/write-carte-totp-sn.html",
        {
            "aidant": aidant,
            "responsable": responsable,
            "form": form,
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
@user_is_responsable_structure
@activity_required
def validate_aidant_carte_totp(request, aidant_id):
    responsable: Aidant = request.user
    aidant = get_object_or_404(Aidant, pk=aidant_id)
    if not responsable.can_see_aidant(aidant):
        raise Http404

    if not hasattr(aidant, "carte_totp"):
        django_messages.error(
            request,
            (
                "Impossible de trouver une carte Aidants Connect associée au compte de "
                f"{aidant.get_full_name()}."
                "Vous devez d’abord lier une carte à son compte."
            ),
        )
        return redirect(
            "espace_responsable_aidant",
            aidant_id=aidant.id,
        )

    if request.method == "POST":
        form = CarteTOTPValidationForm(request.POST)
    else:
        form = CarteTOTPValidationForm()

    if form.is_valid():
        token = form.cleaned_data["otp_token"]
        totp_device = TOTPDevice.objects.get(
            key=aidant.carte_totp.seed, user_id=aidant.id
        )
        valid = totp_device.verify_token(token)
        if valid:
            with transaction.atomic():
                totp_device.tolerance = 1
                totp_device.confirmed = True
                totp_device.save()
                Journal.log_card_validation(
                    responsable, aidant, aidant.carte_totp.serial_number
                )
                # check if the validation request is for the responsable
                if responsable.id == aidant.id:
                    # get all organisations aidant is responsable
                    valid_organisation_requests = OrganisationRequest.objects.filter(
                        organisation__in=responsable.responsable_de.all()
                    )
                    # close all validated requests
                    for organisation_request in valid_organisation_requests:
                        if (
                            organisation_request.status
                            == RequestStatusConstants.VALIDATED.name
                        ):
                            organisation_request.status = (
                                RequestStatusConstants.CLOSED.name
                            )
                            organisation_request.save()
            django_messages.success(
                request,
                (
                    "Tout s’est bien passé, le compte de "
                    f"{aidant.get_full_name()} est prêt !"
                ),
            )
            return redirect(
                "espace_responsable_aidant",
                aidant_id=aidant.id,
            )
        else:
            django_messages.error(request, "Ce code n’est pas valide.")

    return render(
        request,
        "aidants_connect_web/espace_responsable/validate-carte-totp.html",
        {"aidant": aidant, "form": form},
    )


@require_http_methods(["GET", "POST"])
@login_required
@user_is_responsable_structure
@activity_required
def new_habilitation_request(request):
    def render_template(request, form):
        return render(
            request,
            "aidants_connect_web/espace_responsable/new-habilitation-request.html",
            {"form": form},
        )

    responsable: Aidant = request.user

    if request.method == "GET":
        form = HabilitationRequestCreationForm(responsable)
        return render_template(request, form)

    form = HabilitationRequestCreationForm(responsable, request.POST)

    if not form.is_valid():
        return render_template(request, form)

    habilitation_request = form.save(commit=False)

    if Aidant.objects.filter(
        email__iexact=habilitation_request.email,
        organisation__in=responsable.responsable_de.all(),
    ).exists():
        django_messages.warning(
            request,
            (
                f"Il existe déjà un compte aidant pour l’adresse e-mail "
                f"{habilitation_request.email}. Vous n’avez pas besoin de déposer une "
                "nouvelle demande pour cette adresse-ci."
            ),
        )
        return render_template(request, form)

    if HabilitationRequest.objects.filter(
        email=habilitation_request.email,
        organisation__in=responsable.responsable_de.all(),
    ):
        django_messages.warning(
            request,
            (
                "Une demande d’habilitation est déjà en cours pour l’adresse e-mail "
                f"{habilitation_request.email}. Vous n’avez pas besoin d’en déposer "
                "une nouvelle."
            ),
        )
        return render_template(request, form)

    habilitation_request.origin = HabilitationRequest.ORIGIN_RESPONSABLE
    habilitation_request.save()
    django_messages.success(
        request,
        (
            f"La requête d’habilitation pour {habilitation_request.first_name} "
            f"{habilitation_request.last_name} a bien été enregistrée."
        ),
    )

    return redirect(
        "espace_responsable_organisation",
        organisation_id=habilitation_request.organisation.id,
    )
