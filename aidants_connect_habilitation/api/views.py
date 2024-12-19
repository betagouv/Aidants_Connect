from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from aidants_connect_habilitation.constants import HabilitationFormStep
from aidants_connect_habilitation.forms import AidantRequestForm, AidantRequestFormSet
from aidants_connect_habilitation.models import AidantRequest
from aidants_connect_habilitation.presenters import ProfileCardAidantRequestPresenter2
from aidants_connect_habilitation.views import (
    LateStageRequestView,
    ProfileCardAidantRequestPresenter,
)


class PersonnelRequestEditView(LateStageRequestView, FormView):
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

        if self.organisation.status not in self.organisation.Status.aidant_registrable:
            raise Http404

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
                object=ProfileCardAidantRequestPresenter(
                    self.organisation, habilitation_request
                )
            )
        )

    def delete(self, request, *args, **kwargs):
        self.aidant_request.delete()
        return HttpResponse(status=202)


class PersonnelRequestView(LateStageRequestView, FormView):
    form_class = AidantRequestFormSet
    form_valid_template_name = "habilitation/generic-habilitation-request-profile-card.html#habilitation-profile-card"  # noqa: E501
    form_invalid_template_name = "forms/form.html"
    empty_permitted = None

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.PERSONNEL

    @property
    def template_name(self):
        return (
            self.form_valid_template_name
            if self._form_valid
            else self.form_invalid_template_name
        )

    def setup(self, request, *args, **kwargs):
        self._form_valid = False
        super().setup(request, *args, **kwargs)
        if self.organisation.status not in self.organisation.Status.aidant_registrable:
            raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empty_permitted"] = self.empty_permitted
        if self.request.method.casefold() == "get":
            kwargs["data"] = self.request.GET

        return {
            **kwargs,
            "organisation": self.organisation,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault(
            "idx", self.kwargs.get("idx", len(context["form"].forms) - 1)
        )
        context["organisation"] = self.organisation
        return (
            self.get_form_valid_context(**context)
            if self._form_valid
            else self.get_form_invalid_context(**context)
        )

    def get_form_valid_context(self, **kwargs):
        kwargs["object"] = ProfileCardAidantRequestPresenter2(
            self.organisation, kwargs["form"][kwargs["idx"]], kwargs["idx"]
        )
        return kwargs

    def get_form_invalid_context(self, **kwargs):
        return kwargs

    def form_valid(self, form):
        self._form_valid = True
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=422)

    def delete(self, request, *args, **kwargs):
        return HttpResponse(status=202)


class PersonnelRequestViewIdx(PersonnelRequestView):
    form_invalid_template_name = "aidants_connect_habilitation/forms/new-habilitation-request-edit-form.html"  # noqa: E501
    extra_context = {}

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.idx = self.extra_context["idx"] = kwargs["idx"]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not (0 <= self.idx < len(form.forms)):
            raise Http404
        return form

    def get_form_invalid_context(self, **kwargs):
        # Prevent calling super().get_  form_invalid_context()
        return kwargs
