from logging import getLogger

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, FormView, TemplateView
from django.views.generic.edit import BaseFormView

from aidants_connect_common.templatetags.ac_common import mailto_href
from aidants_connect_web.constants import NotificationType
from aidants_connect_web.forms import SwitchMainAidantOrganisationForm, ValidateCGUForm
from aidants_connect_web.models import Aidant, Journal, Notification, Organisation

logger = getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class Home(TemplateView):
    template_name = "aidants_connect_web/espace_aidant/home.html"

    def get_context_data(self, **kwargs):
        user: Aidant = self.request.user
        return {
            **super().get_context_data(**kwargs),
            "aidant": user,
            "notifications": Notification.objects.get_displayable_for_user(user),
            "notification_type": NotificationType,
            "sos_href": mailto_href(
                recipient="contact@aidantsconnect.beta.gouv.fr",
                subject="sos",
                body=(
                    f"Bonjour, je suis {user.get_full_name()}, de la structure"
                    f"{user.organisation}, j’aimerais que vous me rappeliez afin "
                    f"de résoudre mon problème (description du problème), "
                    f"voici mon numéro (numéro de téléphone)"
                ),
            ),
            "sandbox_url": settings.SANDBOX_URL,
        }


@method_decorator(login_required, name="dispatch")
class OrganisationView(DetailView):
    template_name = "aidants_connect_web/espace_aidant/organisation.html"
    context_object_name = "organisation"
    model = Organisation

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        context = self.get_context_data(
            object=self.object, **self.get_organisation_context_data()
        )
        return self.render_to_response(context)

    def get_object(self, queryset=None):
        self.aidant: Aidant = self.request.user
        self.organisation: Organisation = self.aidant.organisation

        if not self.organisation:
            django_messages.error(
                self.request, "Vous n'êtes pas rattaché à une organisation."
            )
            return redirect("espace_aidant_home")
        return self.organisation

    def get_organisation_context_data(self, **kwargs):
        return {
            "aidant": self.aidant,
            "organisation_active_aidants": (
                self.organisation.aidants.active().order_by("last_name")
            ),
        }


@method_decorator(login_required, name="dispatch")
class ValidateCGU(FormView):
    template_name = "aidants_connect_web/espace_aidant/validate_cgu.html"
    form_class = ValidateCGUForm
    success_url = reverse_lazy("espace_aidant_home")

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs["aidant"] = self.aidant
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        self.aidant.validated_cgu_version = settings.CGU_CURRENT_VERSION
        self.aidant.save(update_fields={"validated_cgu_version"})
        django_messages.success(
            self.request, "Merci d’avoir validé les CGU Aidants Connect."
        )
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class SwitchMainOrganisation(BaseFormView):
    form_class = SwitchMainAidantOrganisationForm
    success_url = reverse_lazy("espace_aidant_home")
    next_url = None

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect("espace_aidant_home")

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "aidant": self.aidant}

    def form_invalid(self, form):
        django_messages.error(
            self.request,
            "Il est impossible de sélectionner cette organisation.",
        )

        logger.error(
            f"Failed to select organisation with ID {form.data['organisation']} "
            f"for aidant {self.aidant} with error(s) {form.errors!r}"
        )

        self.next_url = form.cleaned_data["next_url"]
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        with transaction.atomic():
            previous_org = self.aidant.organisation
            self.aidant.organisation = form.cleaned_data["organisation"]
            self.aidant.save(update_fields={"organisation"})
            Journal.log_switch_organisation(self.aidant, previous_org)

        django_messages.success(
            self.request,
            f"Organisation {self.aidant.organisation.name} selectionnée",
        )

        self.next_url = form.cleaned_data["next_url"]
        return super().form_valid(form)

    def get_success_url(self):
        return self.next_url or super().get_success_url()
