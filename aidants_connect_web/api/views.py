from django.http import Http404, HttpResponse
from django.views.generic import FormView

from rest_framework import viewsets

from aidants_connect_web.api.serializers import OrganisationSerializer
from aidants_connect_web.decorators import responsable_logged_required
from aidants_connect_web.forms import NewHabilitationRequestForm
from aidants_connect_web.models import Aidant, Organisation
from aidants_connect_web.views.espace_responsable import (
    HabilitationRequestItemPresenter,
)


class OrganisationViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    queryset = Organisation.objects.filter(is_active=True).order_by("pk").all()
    serializer_class = OrganisationSerializer


@responsable_logged_required
class NewHabilitationRequestSubmitNew(FormView):
    form_class = NewHabilitationRequestForm
    form_valid_template_name = "aidants_connect_web/espace_responsable/new-habilitation-request.html#habilitation-profile-card"  # noqa: E501
    form_invalid_template_name = "forms/form.html#form"
    allow_empty = False

    @property
    def template_name(self):
        return (
            self.form_valid_template_name
            if self._form_valid
            else self.form_invalid_template_name
        )

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self._form_valid = False
        self.referent: Aidant = request.user

    def get_form_kwargs(self):
        hr_extra_kwargs = {}
        if self.allow_empty is False:
            hr_extra_kwargs["empty_permitted"] = False

        kwargs = {
            **super().get_form_kwargs(),
            "form_kwargs": {
                "habilitation_requests": {
                    "form_kwargs": {"referent": self.referent, **hr_extra_kwargs},
                }
            },
        }

        if self.request.method == "GET":
            kwargs["data"] = self.request.GET

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault(
            "idx", len(context["form"]["habilitation_requests"].forms) - 1
        )
        return (
            self.get_form_valid_context(**context)
            if self._form_valid
            else self.get_form_invalid_context(**context)
        )

    def get_form_valid_context(self, **kwargs):
        kwargs["object"] = HabilitationRequestItemPresenter(
            kwargs["form"]["habilitation_requests"].forms[kwargs["idx"]], kwargs["idx"]
        )
        return kwargs

    def get_form_invalid_context(self, **kwargs):
        kwargs["form"] = kwargs["form"]["habilitation_requests"].forms[kwargs["idx"]]
        return kwargs

    def form_valid(self, form):
        self._form_valid = True
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=422)

    def delete(self, request, *args, **kwargs):
        return HttpResponse(status=202)


@responsable_logged_required
class NewHabilitationRequestSubmitNewEdit(NewHabilitationRequestSubmitNew):
    form_invalid_template_name = "aidants_connect_web/espace_responsable/new-habilitation-request-edit-form.html"  # noqa: E501
    extra_context = {}
    allow_empty = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.idx = self.extra_context["idx"] = kwargs["idx"]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not (0 <= self.idx < len(form["habilitation_requests"].forms)):
            raise Http404
        return form

    def get_form_invalid_context(self, **kwargs):
        # Prevent calling super().get_form_invalid_context()
        return kwargs
