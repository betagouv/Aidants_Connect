from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView, RedirectView

from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    IssuerForm,
    OrganisationRequestForm,
)
from aidants_connect_habilitation.models import Issuer, OrganisationRequest


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


class RequestDraftView(FormView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.issuer = get_object_or_404(Issuer, issuer_id=kwargs.get("issuer_id"))


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


class ModifyOrganisationRequestFormView(NewOrganisationRequestFormView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.initial_org_request = get_object_or_404(
            OrganisationRequest, draft_id=self.kwargs.get("draft_id")
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.initial_org_request}


class AidantsRequestFormView(RequestDraftView):
    template_name = "aidants_form.html"
    form_class = AidantRequestFormSet

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation: OrganisationRequest = get_object_or_404(
            OrganisationRequest, draft_id=self.kwargs.get("draft_id")
        )

    def form_valid(self, form):
        for sub_form in form.forms:
            sub_form.instance.organisation = self.organisation
        form.save()
        self.organisation.confirm_request()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "issuer": self.issuer}

    def get_success_url(self):
        return reverse("habilitation_new_issuer")
