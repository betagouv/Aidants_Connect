from logging import getLogger

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template.defaultfilters import filesizeformat
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from django.views.generic.edit import BaseFormView

from aidants_connect_common.templatetags.ac_common import mailto_href
from aidants_connect_web.forms import SwitchMainAidantOrganisationForm, ValidateCGUForm
from aidants_connect_web.models import Aidant, Journal, Notification

logger = getLogger()


@method_decorator(login_required, name="dispatch")
class Home(TemplateView):
    template_name = "aidants_connect_web/espace_aidant/home.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.user: Aidant = self.request.user
        self.tiles_heading_tag = "h4"

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "aidant": self.user,
                "notifications": Notification.objects.get_displayable_for_user(
                    self.user
                ),
                "main_tiles": self.get_main_tiles(),
                "resources_tiles": self.get_resources_tiles(),
                "sandbox_url": settings.SANDBOX_URL,
            }
        )
        return super().get_context_data(**kwargs)

    def get_main_tiles(self):
        email_body = (
            f"Bonjour, je suis {self.user.get_full_name()}, de la structure "
            f"{self.user.organisation}, j’aimerais que vous me rappeliez afin de "
            "résoudre mon problème (description du problème), voici mon numéro "
            "(numéro de téléphone)"
        )

        common_infos = {
            "extra_classes": "fr-tile--horizontal fr-tile--sm",
            "heading_tag": "h2",
        }

        return [
            {
                **common_infos,
                "title": "Créer un mandat",
                "url": reverse("new_mandat"),
                "svg_path": static(
                    "dsfr/dist/artwork/pictograms/document/document-add.svg"
                ),
            },
            {
                **common_infos,
                "id": "view-mandats",
                "title": "Accéder aux mandats",
                "url": reverse("usagers"),
                "svg_path": static("dsfr/dist/artwork/pictograms/digital/search.svg"),
            },
            {
                **common_infos,
                "title": "Contacter lʼéquipe",
                "url": mailto_href(
                    recipient="contact@aidantsconnect.beta.gouv.fr",
                    subject="sos",
                    body=email_body,
                ),
                "svg_path": static(
                    "dsfr/dist/artwork/pictograms/digital/mail-send.svg"
                ),
            },
        ]

    def get_resources_tiles(self):
        def tile_attr_from_file(filepath: str) -> dict:
            size = filesizeformat(staticfiles_storage.size(filepath))
            return {
                "description": f"PDF - {size}",
                "link": static(filepath),
                "heading_tag": self.tiles_heading_tag,
            }

        tiles = {
            "Bien démarrer": [
                {
                    "title": "S’authentifier sur la plateforme Aidants Connect",
                    **tile_attr_from_file(
                        "guides_aidants_connect/AC_Guide_Sauthentifier.pdf"
                    ),
                },
                {
                    "title": "Créer un mandat avec un usager",
                    **tile_attr_from_file(
                        "guides_aidants_connect/AC_Guide_CreerUnMandat.pdf"
                    ),
                },
                {
                    "title": "Réaliser la démarche avec un usager",
                    **tile_attr_from_file(
                        "guides_aidants_connect/AC_Guide_RealiserLaDemarche.pdf"
                    ),
                },
            ],
            "M’entraîner": [
                {
                    "title": "Tutoriel interactif",
                    "link": "https://www.etsijaccompagnais.fr/tutoriel-aidants-connect",
                    "description": "etsijaccompagnais.fr",
                    "new_tab": True,
                    "heading_tag": self.tiles_heading_tag,
                },
                *(
                    []
                    if settings.SANDBOX_URL
                    else [
                        {
                            "title": "Site bac à sable",
                            "link": settings.SANDBOX_URL,
                            "description": "aidantsconnect.beta.gouv.fr",
                            "new_tab": True,
                            "heading_tag": self.tiles_heading_tag,
                        }
                    ]
                ),
            ],
        }

        return tiles


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
