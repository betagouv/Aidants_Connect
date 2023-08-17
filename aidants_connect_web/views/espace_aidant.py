from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView

from aidants_connect_common.templatetags.ac_common import mailto_href
from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.forms import SwitchMainAidantOrganisationForm, ValidateCGUForm
from aidants_connect_web.models import Aidant, Journal, Organisation


@login_required
def home(request):
    aidant = request.user
    sos_href = mailto_href(
        recipient="contact@aidantsconnect.beta.gouv.fr",
        subject="sos",
        body=(
            "Bonjour, je suis (nom,prénom), de la structure (nom de structure), "
            "j’aimerais que vous me rappeliez afin de résoudre mon problème "
            "(description du problème), voici mon numéro (numéro de téléphone)"
        ),
    )
    return render(
        request,
        "aidants_connect_web/espace_aidant/home.html",
        {
            "aidant": aidant,
            "sos_href": sos_href,
            "sandbox_url": settings.SANDBOX_URL,
        },
    )


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
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "organisation_active_aidants": (
                self.organisation.aidants.active().order_by("last_name")
            ),
        }


@login_required
def validate_cgus(request):
    aidant = request.user
    form = ValidateCGUForm()
    if request.method == "POST":
        form = ValidateCGUForm(request.POST)
        if form.is_valid():
            aidant.validated_cgu_version = settings.CGU_CURRENT_VERSION
            aidant.save()
            django_messages.success(
                request, "Merci d’avoir validé les CGU Aidants Connect."
            )
            return redirect("espace_aidant_home")

    return render(
        request,
        "aidants_connect_web/espace_aidant/validate_cgu.html",
        {
            "aidant": aidant,
            "form": form,
        },
    )


@login_required
@activity_required
@user_is_aidant
@require_http_methods(["GET", "POST"])
def switch_main_organisation(request: HttpRequest):
    aidant: Aidant = request.user

    if request.method == "GET":
        form = SwitchMainAidantOrganisationForm(
            aidant, next_url=request.GET.get("next", "")
        )
        return render(
            request,
            "aidants_connect_web/espace_aidant/switch_main_organisation.html",
            {
                "aidant": aidant,
                "organisations": aidant.organisations,
                "form": form,
                "disable_change_organisation": True,
            },
        )

    form = SwitchMainAidantOrganisationForm(aidant, data=request.POST)
    if not form.is_valid():
        django_messages.error(
            request,
            "Il est impossible de vous déplacer dans cette organisation.",
        )
        return redirect("espace_aidant_switch_main_organisation")

    data = form.cleaned_data

    new_org = data.get("organisation")
    previous_org = aidant.organisation
    aidant.organisation = new_org
    aidant.save()

    Journal.log_switch_organisation(aidant, previous_org)

    django_messages.success(
        request,
        f"Votre organisation active est maintenant {new_org} — {new_org.address}.",
    )

    default_next = reverse("espace_aidant_home")
    next_url = data.get("next_url")
    next_url = unquote(next_url) if next_url else default_next

    return HttpResponseRedirect(next_url)
