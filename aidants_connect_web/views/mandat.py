import logging
from datetime import date
from typing import Collection

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import formats, timezone
from django.views.generic import FormView, TemplateView, View

from aidants_connect_common.utils.constants import AuthorizationDurations
from aidants_connect_web.decorators import (
    activity_required,
    aidant_logged_with_activity_required,
    user_is_aidant,
)
from aidants_connect_web.forms import MandatForm, RecapMandatForm
from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    Connection,
    Journal,
    Mandat,
    Usager,
)
from aidants_connect_web.utilities import (
    generate_attestation_hash,
    generate_mailto_link,
    generate_qrcode_png,
)
from aidants_connect_web.views.service import humanize_demarche_names

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class RequireConnectionObjectMixin(View):
    def dispatch(self, request, *args, **kwargs):
        connection_id = request.session.get("connection")

        if not connection_id:
            log.error("No connection id found in session")
            return redirect("espace_aidant_home")

        self.connection: Connection = Connection.objects.get(pk=connection_id)
        self.aidant: Aidant = request.user

        return super().dispatch(request, *args, **kwargs)


@aidant_logged_with_activity_required
class NewMandat(FormView):
    form_class = MandatForm
    template_name = "aidants_connect_web/new_mandat/new_mandat.html"

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user

        try:
            self.connection = Connection.objects.get(
                pk=request.session.get("connection")
            )
        except Connection.DoesNotExist:
            self.connection = None

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "aidant": self.aidant}

    def get_initial(self):
        return (
            {}
            if self.connection is None
            else {
                "duree": self.connection.duree_keyword,
                "is_remote": self.connection.mandat_is_remote,
                "demarche": self.connection.demarches,
                "user_phone": self.connection.user_phone,
            }
        )

    def get_success_url(self):
        return reverse("fc_authorize")

    def form_valid(self, form: MandatForm):
        data = form.cleaned_data

        self.connection = Connection.objects.create(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            demarches=data["demarche"],
            duree_keyword=data["duree"],
            mandat_is_remote=data["is_remote"],
            user_phone=data["user_phone"],
        )

        self.request.session["connection"] = self.connection.pk

        return super().form_valid(form)


@aidant_logged_with_activity_required
class NewMandatRecap(RequireConnectionObjectMixin, FormView):
    form_class = RecapMandatForm
    template_name = "aidants_connect_web/new_mandat/new_mandat_recap.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "usager": self.connection.usager,
            "demarches": [
                humanize_demarche_names(demarche)
                for demarche in self.connection.demarches
            ],
            "duree": self.connection.get_duree_keyword_display(),
            "is_remote": self.connection.mandat_is_remote,
        }

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "aidant": self.aidant}

    def form_valid(self, form):
        fixed_date = timezone.now()
        expiration_date = AuthorizationDurations.expiration(
            self.connection.duree_keyword, fixed_date
        )

        try:
            self.connection.demarches.sort()

            # Update user phone before creating mandate
            if self.connection.user_phone:
                self.connection.usager.phone = self.connection.user_phone
                self.connection.usager.save()

            # Create a mandat
            mandat = Mandat.objects.create(
                organisation=self.aidant.organisation,
                usager=self.connection.usager,
                duree_keyword=self.connection.duree_keyword,
                is_remote=self.connection.mandat_is_remote,
                expiration_date=expiration_date,
            )

            # Add a Journal 'create_attestation' action
            Journal.log_attestation_creation(
                aidant=self.aidant,
                usager=self.connection.usager,
                demarches=self.connection.demarches,
                is_remote_mandat=self.connection.mandat_is_remote,
                access_token=self.connection.access_token,
                attestation_hash=generate_attestation_hash(
                    self.aidant,
                    self.connection.usager,
                    self.connection.demarches,
                    expiration_date,
                ),
                mandat=mandat,
                duree=AuthorizationDurations.duration(
                    self.connection.duree_keyword, fixed_date
                ),
            )

            # This loop creates one `autorisation` object per `démarche` in the form
            for demarche in self.connection.demarches:
                # Revoke existing demarche autorisation(s)
                similar_active_autorisations = Autorisation.objects.active().filter(
                    mandat__organisation=self.aidant.organisation,
                    mandat__usager=self.connection.usager,
                    demarche=demarche,
                )
                for similar_active_autorisation in similar_active_autorisations:
                    similar_active_autorisation.revoke(
                        aidant=self.aidant, revocation_date=fixed_date
                    )

                # Create new demarche autorisation
                autorisation = Autorisation.objects.create(
                    mandat=mandat,
                    demarche=demarche,
                    last_renewal_token=self.connection.access_token,
                )
                Journal.log_autorisation_creation(autorisation, self.aidant)

        except AttributeError as error:
            log.error("Error happened in Recap")
            log.error(error)
            django_messages.error(
                self.request, f"Error with Usager attribute : {error}"
            )
            return redirect("espace_aidant_home")

        except IntegrityError as error:
            log.error("Error happened in Recap")
            log.error(error)
            django_messages.error(self.request, f"No Usager was given : {error}")
            return redirect("espace_aidant_home")

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("new_mandat_success")


@aidant_logged_with_activity_required
class NewMandateSuccess(RequireConnectionObjectMixin, TemplateView):
    template_name = "aidants_connect_web/new_mandat/new_mandat_success.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "usager": self.connection.usager,
        }


@aidant_logged_with_activity_required
class AttestationProject(RequireConnectionObjectMixin, TemplateView):
    template_name = "aidants_connect_web/attestation.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "usager": self.connection.usager,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [
                humanize_demarche_names(demarche)
                for demarche in self.connection.demarches
            ],
            "duree": self.connection.get_duree_keyword_display(),
            "current_mandat_template": settings.MANDAT_TEMPLATE_PATH,
        }


@login_required
@user_is_aidant
@activity_required
def attestation_final(request):
    connection_id = request.session.get("connection")
    if not connection_id:
        log.error("No connection id found in session")
        return redirect("espace_aidant_home")

    connection = Connection.objects.get(pk=connection_id)

    aidant: Aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    # Django magic :
    # https://docs.djangoproject.com/en/3.0/ref/models/instances/#django.db.models.Model.get_FOO_display
    duree = connection.get_duree_keyword_display()

    return __attestation_visualisation(
        request,
        settings.MANDAT_TEMPLATE_PATH,
        usager,
        aidant,
        date.today(),
        demarches,
        duree,
    )


@login_required
@user_is_aidant
@activity_required
def attestation_visualisation(request, mandat_id):
    aidant: Aidant = request.user
    mandat_query_set = Mandat.objects.filter(pk=mandat_id)
    if mandat_query_set.count() != 1:
        mailto_body = render_to_string(
            "aidants_connect_web/mandate_visualisation_errors/not_found_email_body.txt",
            request=request,
            context={"mandat_id": mandat_id},
        )

        return render(
            request,
            "aidants_connect_web/mandate_visualisation_errors/error_page.html",
            {
                "mandat_id": mandat_id,
                "support_email": settings.SUPPORT_EMAIL,
                "mailto": generate_mailto_link(
                    settings.SUPPORT_EMAIL,
                    f"Problème en essayant de visualiser le mandat n°{mandat_id}",
                    mailto_body,
                ),
            },
        )

    mandat: Mandat = mandat_query_set.first()
    template = mandat.get_mandate_template_path()

    if template is not None:
        # At this point, the generated QR code on the mandate comes from an independant
        # HTTP request. Normally, what we should do is to modifiy how this HTTP request
        # is done so that the mandate ID is passed during the request. But the mandate
        # template can't be modified anymore because that would change their hash and
        # defeat the algorithm that recovers the original mandate template from the
        # journal entries. The only found solution, which is not nice, is to retain the
        # mandate ID as a session state. Please forgive us for what we did...
        request.session["qr_code_mandat_id"] = mandat_id
        modified = False
    else:
        template = settings.MANDAT_TEMPLATE_PATH
        modified = True

    procedures = [it.demarche for it in mandat.autorisations.all()]
    return __attestation_visualisation(
        request,
        template,
        mandat.usager,
        aidant,
        mandat.creation_date.date(),
        procedures,
        mandat.get_duree_keyword_display(),
        modified=modified,
    )


def __attestation_visualisation(
    request,
    template: str,
    usager: Usager,
    aidant: Aidant,
    attestation_date: date,
    demarches: Collection[str],
    duree: str,
    modified: bool = False,
):
    return render(
        request,
        "aidants_connect_web/attestation.html",
        {
            "usager": usager,
            "aidant": aidant,
            "date": formats.date_format(attestation_date, "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
            "current_mandat_template": template,
            "final": True,
            "modified": modified,
        },
    )


@login_required
@user_is_aidant
@activity_required
def attestation_qrcode(request):
    attestation_hash = None
    connection = request.session.get("connection", None)
    mandat_id = request.session.pop("qr_code_mandat_id", None)

    if mandat_id is not None:
        attestation_hash = Mandat.get_attestation_hash_or_none(mandat_id)

    elif connection is not None:
        connection = Connection.objects.get(pk=connection)
        aidant: Aidant = request.user

        journal_create_attestation = aidant.get_journal_create_attestation(
            connection.access_token
        )
        if journal_create_attestation is not None:
            attestation_hash = journal_create_attestation.attestation_hash

    if attestation_hash is not None:
        qrcode_png = generate_qrcode_png(attestation_hash)
    else:
        with open(finders.find("images/empty_qr_code.png"), "rb") as f:
            qrcode_png = f.read()

    return HttpResponse(qrcode_png, "image/png")
