from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, RedirectView, TemplateView, View
from django.views.generic.base import ContextMixin

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_habilitation.constants import HabilitationFormStep
from aidants_connect_habilitation.forms import (
    IssuerForm,
    OrganisationRequestForm,
    PersonnelForm,
    ValidationForm,
)
from aidants_connect_habilitation.models import (
    Issuer,
    IssuerEmailConfirmation,
    OrganisationRequest,
)

__all__ = [
    "NewHabilitationView",
    "NewIssuerFormView",
    "IssuerEmailConfirmationWaitingView",
    "IssuerEmailConfirmationView",
    "IssuerPageView",
    "ModifyIssuerFormView",
    "NewOrganisationRequestFormView",
    "ModifyOrganisationRequestFormView",
    "PersonnelRequestFormView",
    "ValidationRequestFormView",
]

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
        self.issuer = get_object_or_404(Issuer, issuer_id=kwargs.get("issuer_id"))

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
    @property
    def step(self) -> HabilitationFormStep:
        raise NotImplementedError()

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(
            OrganisationRequest, draft_id=kwargs.get("draft_id")
        )


"""Real views"""


class NewHabilitationView(RedirectView):
    permanent = True
    pattern_name = "habilitation_new_issuer"


class NewIssuerFormView(HabilitationStepMixin, FormView):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    template_name = "issuer_form.html"
    form_class = IssuerForm

    def form_valid(self, form):
        self.saved_model: Issuer = form.save()
        IssuerEmailConfirmation.for_issuer(self.saved_model).send(self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "step": self.step}


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
                "email_confirmation_sent": True,
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
            self.__continue()
            if self.issuer.email_verified
            else super().get(request, *args, **kwargs)
        )

    def post(self, request, *args, **kwargs):
        return (
            self.__continue()
            if self.email_confirmation.confirm()
            else self.render_to_response(
                {**self.get_context_data(**kwargs), "email_confirmation_expired": True}
            )
        )

    def __continue(self):
        return redirect(
            "habilitation_new_organisation", issuer_id=self.issuer.issuer_id
        )


class IssuerPageView(VerifiedEmailIssuerView, TemplateView):
    template_name = "issuer_space.html"


class ModifyIssuerFormView(VerifiedEmailIssuerView, NewIssuerFormView):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.issuer}

    def get_success_url(self):
        return reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class NewOrganisationRequestFormView(
    HabilitationStepMixin, VerifiedEmailIssuerView, FormView
):
    template_name = "organisation_form.html"
    form_class = OrganisationRequestForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ORGANISATION

    def form_valid(self, form):
        form.instance.issuer = self.issuer
        self.saved_model: OrganisationRequest = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "draft_id": str(self.saved_model.draft_id),
            },
        )


class ModifyOrganisationRequestFormView(
    LateStageRequestView, NewOrganisationRequestFormView
):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ORGANISATION

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.organisation}


class PersonnelRequestFormView(LateStageRequestView, HabilitationStepMixin, FormView):
    template_name = "personnel_form.html"
    form_class = PersonnelForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.PERSONNEL

    def form_valid(self, form):
        form.save(self.organisation)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer_form": IssuerForm(instance=self.issuer, render_non_editable=True),
            "organisation": self.organisation,
        }

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        data_privacy_officer = self.organisation.data_privacy_officer
        manager = self.organisation.manager
        aidant_qs = self.organisation.aidant_requests

        if aidant_qs.count() > 0:
            form_kwargs[
                f"{PersonnelForm.AIDANTS_FORMSET_PREFIX}_queryset"
            ] = aidant_qs.all()

        if data_privacy_officer:
            form_kwargs[
                f"{PersonnelForm.DPO_FORM_PREFIX}_instance"
            ] = data_privacy_officer

        if manager:
            form_kwargs[f"{PersonnelForm.MANAGER_FORM_PREFIX}_instance"] = manager

        return form_kwargs

    def get_success_url(self):
        return reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "draft_id": str(self.organisation.draft_id),
            },
        )


class ValidationRequestFormView(LateStageRequestView, HabilitationStepMixin, FormView):
    template_name = "validation_form.html"
    form_class = ValidationForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SUMMARY

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "organisation": self.organisation,
            "aidants": self.organisation.aidant_requests,
            "type_other": RequestOriginConstants.OTHER.value,
        }

    def get_success_url(self):
        return reverse("habilitation_new_issuer")
