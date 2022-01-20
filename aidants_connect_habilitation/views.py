from typing import Union

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView, RedirectView

from aidants_connect_habilitation.forms import (
    OrganisationRequestForm,
    AidantRequestFormSet,
    IssuerForm,
)
from aidants_connect_habilitation.models import Issuer, OrganisationRequest


class NewHabilitationView(RedirectView):
    permanent = True
    pattern_name = "habilitation_new_issuer"


class IssuerFormView(FormView):
    template_name = "issuer_form.html"
    form_class = IssuerForm

    def __init__(self):
        super().__init__()
        self.saved_model: Issuer = None
        self.initial_issuer: Union[Issuer, None] = None

    def form_valid(self, form):
        self.saved_model = form.save()
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == "get":
            issuer_id = self.kwargs.get("issuer_id")
            if issuer_id:
                self.initial_issuer = get_object_or_404(Issuer, issuer_id=issuer_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.initial_issuer:
            kwargs.update({"instance": self.initial_issuer})
        return kwargs

    def get_success_url(self):
        return reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class IssuerDraftView(FormView):
    def __init__(self):
        super().__init__()
        self.issuer: Issuer = None

    def dispatch(self, request, *args, **kwargs):
        self.issuer = get_object_or_404(Issuer, issuer_id=kwargs.get("issuer_id"))
        return super().dispatch(request, *args, **kwargs)


class OrganisationRequestFormView(IssuerDraftView):
    template_name = "organisation_form.html"
    form_class = OrganisationRequestForm

    def __init__(self):
        super().__init__()
        self.saved_model: OrganisationRequest = None
        self.initial_org_request: Union[OrganisationRequest, None] = None

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == "get":
            draft_id = self.kwargs.get("draft_id")
            if draft_id:
                self.initial_org_request = get_object_or_404(
                    OrganisationRequest, draft_id=draft_id
                )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.issuer = self.issuer
        self.saved_model = form.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.initial_org_request:
            kwargs.update({"instance": self.initial_org_request})
        return kwargs

    def get_success_url(self):
        return reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "draft_id": str(self.saved_model.draft_id),
            },
        )


class AidantsRequestFormView(IssuerDraftView):
    template_name = "aidants_form.html"
    form_class = AidantRequestFormSet

    def __init__(self):
        super().__init__()
        self.organisation: Union[OrganisationRequest, None] = None

    def dispatch(self, request, *args, **kwargs):
        self.organisation = get_object_or_404(
            OrganisationRequest, draft_id=kwargs.get("draft_id")
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        for sub_form in form.forms:
            sub_form.instance.organisation = self.organisation
        form.save()
        self.organisation.confirm_request()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"issuer": self.issuer})
        return context

    def get_success_url(self):
        return reverse("habilitation_new_issuer")
