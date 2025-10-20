from abc import ABC
from uuid import UUID

from django.conf import settings
from django.forms import Form, model_to_dict
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import FormView, RedirectView, TemplateView, View
from django.views.generic.base import ContextMixin
from django.views.generic.edit import UpdateView

from aidants_connect_common.constants import (
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_common.utils import issuer_exists_send_reminder_email
from aidants_connect_common.views import (
    FormationRegistrationView as CommonFormationRegistrationView,
)
from aidants_connect_habilitation.constants import HabilitationFormStep
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    IssuerForm,
    OrganisationRequestForm,
    OrganisationSiretVerificationRequestForm,
    ReferentForm,
    ValidationForm,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    IssuerEmailConfirmation,
    Manager,
    OrganisationRequest,
)
from aidants_connect_web.models import Organisation

__all__ = [
    "NewHabilitationView",
    "NewIssuerFormView",
    "IssuerEmailConfirmationWaitingView",
    "IssuerEmailConfirmationView",
    "IssuerPageView",
    "ModifyIssuerFormView",
    "NewOrganisationSiretVerificationRequestFormView",
    "NewOrganisationSiretNavigationView",
    "NewOrganisationRequestFormView",
    "ModifyOrganisationRequestFormView",
    "PersonnelRequestFormView",
    "ValidationRequestFormView",
    "ReadonlyRequestView",
    "AidantFormationRegistrationView",
    "HabilitationRequestCancelationView",
    "ReferentRequestFormView",
    "ManagerFormationRegistrationView",
]

from aidants_connect_habilitation.presenters import ProfileCardAidantRequestPresenter
from aidants_connect_web.models import Aidant, HabilitationRequest

"""Mixins"""


class HabilitationStepMixin(ContextMixin):
    @property
    def step(self) -> HabilitationFormStep:
        raise NotImplementedError()

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "step": self.step,
        }


class CheckIssuerMixin(ContextMixin, View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            uuid = UUID(kwargs.get("issuer_id"))
        except ValueError:
            raise Http404()
        self.issuer = get_object_or_404(Issuer, issuer_id=uuid)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer": self.issuer,
        }


class VerifiedEmailIssuerView(CheckIssuerMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not self.issuer.email_verified:
            return redirect(
                "habilitation_issuer_email_confirmation_waiting",
                issuer_id=self.issuer.issuer_id,
            )

        return super().dispatch(request, *args, **kwargs)


class LateStageRequestView(VerifiedEmailIssuerView, View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            uuid = UUID(kwargs.get("uuid"))
        except ValueError:
            raise Http404()
        self.organisation: OrganisationRequest = get_object_or_404(
            OrganisationRequest, uuid=uuid, issuer=self.issuer
        )


class OnlyNewRequestsView(HabilitationStepMixin, LateStageRequestView, ABC):
    def dispatch(self, request, *args, **kwargs):
        if not self.issuer.email_verified:
            # Duplicate logic of VerifiedEmailIssuerView
            # because we want to check issuer email first.
            return redirect(
                "habilitation_issuer_email_confirmation_waiting",
                issuer_id=self.issuer.issuer_id,
            )

        if self.organisation.status not in RequestStatusConstants.validatable:
            return redirect(
                "habilitation_organisation_view",
                issuer_id=self.issuer.issuer_id,
                uuid=self.organisation.uuid,
            )

        return super().dispatch(request, *args, **kwargs)


"""Real views"""


class NewHabilitationView(RedirectView):
    permanent = True
    pattern_name = "habilitation_new_issuer"


class NewIssuerFormView(HabilitationStepMixin, FormView):
    template_name = "issuer_form.html"
    form_class = IssuerForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def form_invalid(self, form: IssuerForm):
        # Gets the error code of all the errors for email, if any
        # See https://docs.djangoproject.com/en/dev/ref/forms/fields/#django.forms.Field.error_messages  # noqa
        email_errors = form.errors.get("email")
        if email_errors:
            error_codes = [error.code for error in form.errors.get("email").as_data()]
            if "unique" in error_codes:
                self.send_issuer_profile_reminder_mail(form.data["email"])
                return render(self.request, "issuer_already_exists_warning.html")
        return super().form_invalid(form)

    def form_valid(self, form: IssuerForm):
        self.saved_model: Issuer = form.save()
        if not self.saved_model.email_verified:
            IssuerEmailConfirmation.for_issuer(self.saved_model).send(self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )

    def send_issuer_profile_reminder_mail(self, email: str):
        issuer: Issuer = Issuer.objects.get(email__iexact=email)

        issuer_exists_send_reminder_email(self.request, issuer)


class IssuerEmailConfirmationWaitingView(
    HabilitationStepMixin, CheckIssuerMixin, TemplateView
):
    template_name = "email_confirmation_waiting.html"

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def post(self, request, *args, **kwargs):
        """Resend a confirmation link"""
        IssuerEmailConfirmation.for_issuer(self.issuer).send(self.request)

        return self.render_to_response(
            {
                **self.get_context_data(**kwargs),
                "support_email": settings.EMAIL_CONFIRMATION_SUPPORT_CONTACT_EMAIL,
                "support_subject": settings.EMAIL_CONFIRMATION_SUPPORT_CONTACT_SUBJECT,
                "support_body": settings.EMAIL_CONFIRMATION_SUPPORT_CONTACT_BODY,
            }
        )


class IssuerEmailConfirmationView(
    HabilitationStepMixin, CheckIssuerMixin, TemplateView
):
    template_name = "email_confirmation_confirm.html"

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.email_confirmation = get_object_or_404(
            IssuerEmailConfirmation, issuer=self.issuer, key=kwargs.get("key")
        )

    def get(self, request, *args, **kwargs):
        return (
            super().get(request, *args, **kwargs)
            if self.email_confirmation.confirm()
            else self.render_to_response(
                {**self.get_context_data(**kwargs), "email_confirmation_expired": True}
            )
        )

    def post(self, request, *args, **kwargs):
        return (
            self.__continue()
            if self.issuer.email_verified
            else self.render_to_response(
                {**self.get_context_data(**kwargs), "email_confirmation_expired": True}
            )
        )

    def __continue(self):
        return redirect(
            "habilitation_siret_verification", issuer_id=self.issuer.issuer_id
        )


class IssuerPageView(VerifiedEmailIssuerView, TemplateView):
    template_name = "issuer_space.html"


class ModifyIssuerFormView(VerifiedEmailIssuerView, NewIssuerFormView):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = None
        if "issuer_id" in kwargs and "uuid" in kwargs:
            self.organisation = get_object_or_404(
                OrganisationRequest,
                issuer__issuer_id=kwargs["issuer_id"],
                uuid=kwargs["uuid"],
            )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.issuer}

    def get_success_url(self):
        if self.organisation:
            return reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": self.saved_model.issuer_id,
                    "uuid": self.organisation.uuid,
                },
            )

        return reverse(
            "habilitation_siret_verification",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class NewOrganisationSiretVerificationRequestFormView(
    HabilitationStepMixin, VerifiedEmailIssuerView, FormView
):
    template_name = (
        "aidants_connect_habilitation/organisation-siret-verification-form-view.html"
    )
    form_class = OrganisationSiretVerificationRequestForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SIRET_VERIFICATION

    def form_valid(self, form):
        self.form = form
        siret = self.form.cleaned_data["siret"]
        orgas = Organisation.objects.filter(siret=siret)
        return self.render_to_response(
            self.get_context_data(
                form=form,
                siret_verified=True,
                siret_value=siret,
                existing_organisations=orgas,
                siret_is_new=not orgas.exists(),
            )
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer_id": f"{self.issuer.issuer_id}",
        }


class NewOrganisationSiretNavigationView(
    HabilitationStepMixin, VerifiedEmailIssuerView, View
):
    """
    Vue de navigation pour rediriger vers la création d'organisation
    dans les cas autorisés.
    """

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SIRET_VERIFICATION

    def post(self, request, *args, **kwargs):
        siret = request.POST.get("siret")
        choice = request.POST.get("organisation_choice")

        orgas = Organisation.objects.filter(siret=siret)

        # Cas de sécurité : ne devrait jamais arriver
        if not siret:
            return redirect(
                "habilitation_siret_verification",
                issuer_id=f"{self.issuer.issuer_id}",
            )

        if not orgas.exists() or (choice and choice == "0"):
            # Cas 1: SIRET nouveau (pas d'organisations en base)
            # Cas 2: Choix explicite "Ma structure n'apparaît pas"
            return redirect(
                "habilitation_new_organisation",
                issuer_id=f"{self.issuer.issuer_id}",
                siret=siret,
            )
        else:
            # Cas de sécurité : ne devrait jamais arriver
            # si le template fonctionne correctement
            return redirect(
                "habilitation_siret_verification",
                issuer_id=f"{self.issuer.issuer_id}",
            )


class NewOrganisationRequestFormView(
    HabilitationStepMixin, VerifiedEmailIssuerView, FormView
):
    template_name = "aidants_connect_habilitation/organisation-form-view.html"
    form_class = OrganisationRequestForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ORGANISATION

    def get_initial(self):
        if "name" in self.request.GET:
            return {
                "siret": self.kwargs.get("siret"),
                "name": self.request.GET.get("name"),
            }
        return {
            "siret": self.kwargs.get("siret"),
        }

    def form_valid(self, form):
        form.instance.issuer = self.issuer
        self.saved_model: OrganisationRequest = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_new_referent",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.saved_model.uuid),
            },
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "type_other_value": RequestOriginConstants.OTHER.value,
            "issuer_id": f"{self.issuer.issuer_id}",
        }


class ModifyOrganisationRequestFormView(
    OnlyNewRequestsView, NewOrganisationRequestFormView
):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ORGANISATION

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.organisation}

    def get_initial(self):
        # heritage from NewOrganisationRequestFormView => get_initial() None for siret
        # because siret is in url on NewOrganisationRequestFormView
        return {
            **(super().get_initial()),
            "siret": self.organisation.siret,
        }


class ReferentRequestFormView(OnlyNewRequestsView, UpdateView):
    template_name = "aidants_connect_habilitation/referent-form-view.html"
    form_class = ReferentForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.REFERENT

    def get_object(self, queryset=None):
        return getattr(self.organisation, "manager", None)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "organisation": self.organisation,
        }

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "organisation": self.organisation,
        }

    def get_success_url(self):
        return reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.organisation.uuid),
            },
        )


class PersonnelRequestFormView(LateStageRequestView, HabilitationStepMixin, FormView):
    template_name = "aidants_connect_habilitation/personnel-form-view.html"
    form_class = AidantRequestFormSet

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.PERSONNEL

    def form_valid(self, form):
        if "partial-submit" in self.request.POST:
            data = self.request.POST.copy()
            total_forms = int(data.get("form-TOTAL_FORMS", 0))
            data["form-TOTAL_FORMS"] = str(total_forms + 1)

            form_kwargs = self.get_form_kwargs()
            form_kwargs.pop("data", None)
            form_kwargs["data"] = data

            new_form = self.form_class(**form_kwargs)
            return self.render_to_response(self.get_context_data(form=new_form))
        else:
            form.save()
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        manager_data = {}
        if self.organisation.manager:
            manager_data = model_to_dict(
                self.organisation.manager,
                fields=["first_name", "last_name", "email", "profession"],
            )
        kwargs.update({"organisation": self.organisation, "manager_data": manager_data})
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "organisation": self.organisation,
        }

    def get_success_url(self):
        return reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.organisation.uuid),
            },
        )


class BaseValidationRequestFormView(
    HabilitationStepMixin, LateStageRequestView, FormView
):
    # fmt: off
    template_name = "aidants_connect_habilitation/validation-request-form-view.html"  # noqa: E501
    # fmt: on
    form_class = ValidationForm
    presenter_class = ProfileCardAidantRequestPresenter

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SUMMARY

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "organisation": self.organisation,
                # using a generator to avoid unneccessary computations
                "habilitation_requests": (
                    self.presenter_class(self.organisation, it)
                    for it in self.organisation.aidant_requests.prefetch_related(
                        "habilitation_request"
                    ).all()
                ),
                "type_other": RequestOriginConstants.OTHER.value,
            }
        )
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse(
            "habilitation_organisation_view",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.organisation.uuid),
            },
        )

    def get_initial(self):
        return {
            "cgu": self.organisation.cgu,
            "not_free": self.organisation.not_free,
            "dpo": self.organisation.dpo,
            "professionals_only": self.organisation.professionals_only,
            "without_elected": self.organisation.without_elected,
        }

    def form_valid(self, form):
        form.save(self.organisation)
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        form: ValidationForm = self.get_form()
        if self.organisation.manager is None:
            form.add_error(
                None,
                "Veuillez ajouter le ou la référente de la structure avant validation.",
            )
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ValidationRequestFormView(OnlyNewRequestsView, BaseValidationRequestFormView):
    pass


class ReadOnlyProfileCardAidantRequestPresenter(ProfileCardAidantRequestPresenter):
    @property
    def summary_second_line_tpl(self):
        return "aidants_connect_habilitation/validation-request-form-view.html#summary-second-line"  # noqa: E501

    @property
    def organisation(self):
        return self.org

    @property
    def habilitation_request(self):
        return self.req.habilitation_request


class ReadonlyRequestView(BaseValidationRequestFormView):
    presenter_class = ReadOnlyProfileCardAidantRequestPresenter


class AidantFormationRegistrationView(
    LateStageRequestView, CommonFormationRegistrationView
):
    def dispatch(self, request, *args, **kwargs):
        self.person = self.get_person()
        if not self.person.habilitation_request:
            raise Http404

        aidant = Aidant.objects.filter(email=self.organisation.manager.email)
        if aidant.exists() and aidant.first().last_login:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get_person(self):
        return get_object_or_404(
            AidantRequest, pk=self.kwargs["aidant_id"], organisation=self.organisation
        )

    def get_cancel_url(self) -> str:
        return self.organisation.get_absolute_url()

    def get_habilitation_request(self) -> HabilitationRequest:
        return self.person.habilitation_request

    def get_success_url(self):
        return self.organisation.get_absolute_url()


class HabilitationRequestCancelationView(LateStageRequestView, FormView):
    form_class = Form
    template_name = "cancel-habilitation-request.html"

    def dispatch(self, request, *args, **kwargs):
        self.person = get_object_or_404(
            AidantRequest, pk=self.kwargs["aidant_id"], organisation=self.organisation
        )

        if (
            not self.person.habilitation_request
            or not self.person.habilitation_request.status_cancellable_by_responsable
        ):
            raise Http404

        aidant = Aidant.objects.filter(email=self.organisation.manager.email)
        if aidant.exists() and aidant.first().last_login:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.person.habilitation_request.cancel_by_responsable()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "request": self.person.habilitation_request,
                "organisation": self.organisation,
            }
        )
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse(
            "habilitation_organisation_view",
            kwargs={"issuer_id": self.issuer.issuer_id, "uuid": self.organisation.uuid},
        )


class ManagerFormationRegistrationView(AidantFormationRegistrationView):
    def get_person(self):
        return get_object_or_404(
            Manager, organisation=self.organisation, is_aidant=True
        )
