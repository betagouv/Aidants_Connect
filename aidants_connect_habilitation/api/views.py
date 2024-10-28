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
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SUMMARY

    def setup(self, request, *args, **kwargs):
        self.success = False
        super().setup(request, *args, **kwargs)
        self.aidant_request = get_object_or_404(
            AidantRequest,
            organisation=self.organisation,
            pk=self.kwargs.get("aidant_id"),
        )

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {
            "organisation": self.organisation,
            "instance": self.aidant_request,
            **super().get_form_kwargs(),
        }

    def get_context_data(self, **kwargs):
        if "habilitation_request" in kwargs:
            kwargs["habilitation_request"] = ProfileCardAidantRequestPresenter(
                kwargs["habilitation_request"]
            )

        kwargs.update(
            {
                "action": reverse(
                    "api_habilitation_aidant_edit",
                    kwargs={
                        "issuer_id": self.organisation.issuer.issuer_id,
                        "uuid": self.organisation.uuid,
                        "aidant_id": self.aidant_request.pk,
                    },
                )
            }
        )
        return super().get_context_data(**kwargs)

    def get_template_names(self):
        if self.success:
            return "aidants_connect_habilitation/validation_request_form_view/_habilitation-request-profile-card.html"  # noqa: E501
        else:
            return "forms/form.html"

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=422)

    def form_valid(self, form):
        habilitation_request = form.save()
        self.success = True
        return self.render_to_response(
            self.get_context_data(habilitation_request=habilitation_request)
        )
