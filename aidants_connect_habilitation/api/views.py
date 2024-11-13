from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from aidants_connect_habilitation.constants import HabilitationFormStep
from aidants_connect_habilitation.forms import AidantRequestForm
from aidants_connect_habilitation.models import AidantRequest
from aidants_connect_habilitation.views import (
    OnlyNewRequestsView,
    ProfileCardAidantRequestPresenter,
)


class PersonnelRequestEditView(OnlyNewRequestsView, FormView):
    form_class = AidantRequestForm

    @property
    def template_name(self):
        return (
            "habilitation/generic-habilitation-request-profile-card.html#habilitation-profile-card"  # noqa: E501
            if self._form_valid
            else "forms/form.html"
        )

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SUMMARY

    def setup(self, request, *args, **kwargs):
        self._form_valid = False
        super().setup(request, *args, **kwargs)
        self.aidant_request = get_object_or_404(
            AidantRequest,
            organisation=self.organisation,
            pk=self.kwargs.get("aidant_id"),
        )

    def get_form_kwargs(self):
        return {
            "organisation": self.organisation,
            "instance": self.aidant_request,
            **super().get_form_kwargs(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return (
            self.get_form_valid_context_data(**context)
            if self._form_valid
            else self.get_form_invalid_context_data(**context)
        )

    def get_form_valid_context_data(self, **kwargs):
        kwargs["action"] = reverse(
            "api_habilitation_aidant_edit",
            kwargs={
                "issuer_id": self.organisation.issuer.issuer_id,
                "uuid": self.organisation.uuid,
                "aidant_id": self.aidant_request.pk,
            },
        )
        return kwargs

    def get_form_invalid_context_data(self, **kwargs):
        return kwargs

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=422)

    def form_valid(self, form):
        habilitation_request = form.save()
        self._form_valid = True
        return self.render_to_response(
            self.get_context_data(
                object=ProfileCardAidantRequestPresenter(habilitation_request)
            )
        )

    def delete(self, request, *args, **kwargs):
        self.aidant_request.delete()
        return HttpResponse(status=202)
