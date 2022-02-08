from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView, RedirectView

from aidants_connect_habilitation.forms import (
    IssuerForm,
    OrganisationRequestForm,
    PersonnelForm,
    ValidationForm,
)
from aidants_connect_habilitation.models import (
    Issuer,
    OrganisationRequest,
)


__all__ = [
    "NewHabilitationView",
    "NewIssuerFormView",
    "ModifyIssuerFormView",
    "NewOrganisationRequestFormView",
    "ModifyOrganisationRequestFormView",
    "PersonnelRequestFormView",
    "ValidationRequestFormView",
]


"""Mixins"""


class RequestDraftView(FormView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.issuer = get_object_or_404(Issuer, issuer_id=kwargs.get("issuer_id"))

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer": self.issuer,
        }


class LateStageRequestDraftView(RequestDraftView):
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
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class ModifyIssuerFormView(NewIssuerFormView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.initial_issuer = get_object_or_404(
            Issuer, issuer_id=self.kwargs.get("issuer_id")
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.initial_issuer}


class NewOrganisationRequestFormView(RequestDraftView):
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
    LateStageRequestDraftView, NewOrganisationRequestFormView
):
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.organisation}


class PersonnelRequestFormView(LateStageRequestDraftView):
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
        }

    def get_success_url(self):
        return reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "draft_id": str(self.organisation.draft_id),
            },
        )


class ValidationRequestFormView(LateStageRequestDraftView):
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
