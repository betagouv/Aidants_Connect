import logging

from django.contrib.auth import logout
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views import View
from django.views.generic import DetailView, FormView

from aidants_connect_common.forms import (
    FollowMyHabilitationRequesrForm,
    FormationRegistrationForm,
)
from aidants_connect_common.models import Formation, FormationOrganization, Region
from aidants_connect_common.utils import issuer_exists_send_reminder_email
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import Aidant, Connection, HabilitationRequest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class RequireConnectionMixin:
    check_connection_expiration = True

    def check_connection(self, request: HttpRequest) -> HttpResponse | Connection:
        connection_id = request.session.get("connection")
        view_location = f"{self.__module__}.{self.__class__.__name__}"

        try:
            connection: Connection = Connection.objects.get(pk=connection_id)
            if connection.is_expired and self.check_connection_expiration:
                log.info(f"Connection has expired @ {view_location}")
                return render(request, "408.html", status=408)

            return connection
        except Exception:
            log.error(
                f"No connection id found for id {connection_id} @ {view_location}"
            )
            logout(request)
            return HttpResponseForbidden()


class RequireConnectionView(RequireConnectionMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if isinstance(result := self.check_connection(request), HttpResponse):
            return result

        self.connection: Connection = result
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)


class FormationRegistrationView(FormView):
    form_class = FormationRegistrationForm
    template_name = "formation/formation-registration.html"

    def dispatch(self, request, *args, **kwargs):
        self.attendant = self.get_habilitation_request()
        if (
            self.attendant.status
            not in ReferentRequestStatuses.formation_registerable()
        ):
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get_habilitation_request(self) -> HabilitationRequest:
        raise NotImplementedError

    def get_cancel_url(self) -> str:
        raise NotImplementedError

    def form_valid(self, form: FormationRegistrationForm):
        with transaction.atomic():
            Formation.objects.exclude(
                pk__in=form.cleaned_data["formations"].values("pk")
            ).for_attendant(self.attendant).unregister_attendant(self.attendant)
            form.cleaned_data["formations"].register_attendant(self.attendant)

        return super().form_valid(form)

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "attendant": self.get_habilitation_request(),
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        return {
            **ctx,
            "registered_to": self.get_habilitation_request().formations.values_list(
                "formation", flat=True
            ),
            "formation_regions": Region.objects.filter(
                pk__in=ctx["form"]
                .fields["formations"]
                .queryset.values_list("organisation__region", flat=True)
            ).distinct(),
            "attendant": self.attendant,
            "cancel_url": self.get_cancel_url(),
        }


class FormationsInformations(DetailView):
    template_name = "formation/_formation-information.html"
    queryset = Region.objects.all()

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "organisations": FormationOrganization.objects.filter(region=self.object),
        }


class FollowMyHabilitationRequestView(FormView):
    template_name = "habilitation/_follow-my-request-form.html"
    form_class = FollowMyHabilitationRequesrForm

    def form_valid(self, form):
        issuer_exists_send_reminder_email(self.request, form.cleaned_data["email"])
        return super().render_to_response(
            self.get_context_data(form=form, success=True)
        )
