from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, RedirectView, TemplateView
from django.views.generic.base import ContextMixin

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
    "ModifyIssuerFormView",
    "NewOrganisationRequestFormView",
    "ModifyOrganisationRequestFormView",
    "PersonnelRequestFormView",
    "ValidationRequestFormView",
]


"""Mixins"""


class CheckIssuerMixin(ContextMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.issuer = get_object_or_404(Issuer, issuer_id=kwargs.get("issuer_id"))

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer": self.issuer,
        }


class VerifiedEmailIssuerFormView(CheckIssuerMixin, FormView):
    def dispatch(self, request, *args, **kwargs):
        if not self.issuer.email_verified:
            return redirect(
                "habilitation_issuer_email_confirmation_waiting",
                issuer_id=self.issuer.issuer_id,
            )

        return super().dispatch(request, *args, **kwargs)


class LateStageRequestFormView(VerifiedEmailIssuerFormView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = get_object_or_404(
            OrganisationRequest, draft_id=kwargs.get("draft_id")
        )


"""Real views"""


class NewHabilitationView(RedirectView):
    permanent = True
    pattern_name = "habilitation_new_issuer"


class NewIssuerFormView(FormView):
    template_name = "issuer_form.html"
    form_class = IssuerForm

    def form_valid(self, form):
        self.saved_model: Issuer = form.save()
        IssuerEmailConfirmation.create(self.saved_model).send()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class IssuerEmailConfirmationWaitingView(CheckIssuerMixin, TemplateView):
    template_name = "email_confirmation_waiting.html"

    def post(self, request, *args, **kwargs):
        """Resend a confirmation link"""
        IssuerEmailConfirmation.create(self.issuer).send()

        return self.render_to_response(
            {**self.get_context_data(**kwargs), "email_confirmation_sent": True}
        )


class IssuerEmailConfirmationView(CheckIssuerMixin, TemplateView):
    template_name = "email_confirmation_confirm.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.email_confirmation = get_object_or_404(
            IssuerEmailConfirmation, issuer=self.issuer, key=kwargs.get("key")
        )

    def post(self, request, *args, **kwargs):
        if self.email_confirmation.confirm():
            return redirect(
                "habilitation_modify_issuer", issuer_id=self.issuer.issuer_id
            )

        return self.render_to_response(
            {**self.get_context_data(**kwargs), "email_confirmation_expired": True}
        )


class ModifyIssuerFormView(VerifiedEmailIssuerFormView, NewIssuerFormView):
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.issuer}

    def get_success_url(self):
        return reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class NewOrganisationRequestFormView(VerifiedEmailIssuerFormView):
    template_name = "organisation_form.html"
    form_class = OrganisationRequestForm

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
    LateStageRequestFormView, NewOrganisationRequestFormView
):
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.organisation}


class PersonnelRequestFormView(LateStageRequestFormView):
    template_name = "personnel_form.html"
    form_class = PersonnelForm

    def form_valid(self, form):
        manager, data_privacy_officer, _ = form.save(self.organisation)
        self.organisation.manager = manager
        self.organisation.data_privacy_officer = data_privacy_officer
        self.organisation.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer_form": IssuerForm(instance=self.issuer, render_non_editable=True),
            "organisation": self.organisation,
        }

    def get_success_url(self):
        return reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "draft_id": str(self.organisation.draft_id),
            },
        )


class ValidationRequestFormView(LateStageRequestFormView):
    template_name = "validation_form.html"
    form_class = ValidationForm

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer": self.issuer,
            "organisation": self.organisation,
            "aidants": self.organisation.aidant_requests,
        }

    def get_success_url(self):
        return reverse("habilitation_new_issuer")
