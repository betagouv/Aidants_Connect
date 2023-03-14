import logging
import re
from datetime import date
from typing import Callable, List
from urllib.parse import unquote_plus
from uuid import uuid4

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db import IntegrityError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import engines
from django.template.backends.django import DjangoTemplates
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import formats, timezone
from django.utils.html import format_html
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, RedirectView, TemplateView, View

from phonenumbers import PhoneNumber

from aidants_connect_common.templatetags.ac_common import mailto
from aidants_connect_common.utils.constants import (
    AuthorizationDurationChoices,
    AuthorizationDurations,
)
from aidants_connect_common.utils.sms_api import SmsApi
from aidants_connect_common.views import RequireConnectionMixin, RequireConnectionView
from aidants_connect_pico_cms.models import MandateTranslation
from aidants_connect_web.decorators import (
    activity_required,
    aidant_logged_with_activity_required,
    user_is_aidant,
)
from aidants_connect_web.forms import (
    IdentityVerificationForm,
    MandatForm,
    PatchedForm,
    RecapMandatForm,
    RemoteConsentMethodChoices,
)
from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    Connection,
    Journal,
    Mandat,
    Organisation,
    Usager,
)
from aidants_connect_web.utilities import generate_attestation_hash, generate_qrcode_png
from aidants_connect_web.views.service import humanize_demarche_names

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class MandatCreationJsFormView(FormView):
    def get_form(self, form_class=None):
        form: PatchedForm = super().get_form(form_class)
        form.widget_attrs(
            "is_remote",
            {
                "data-action": "new-mandat-form#isRemoteChanged",
                "data-new-mandat-form-target": "isRemoteInput",
            },
        )
        form.widget_attrs(
            "remote_constent_method",
            {
                "data-action": "new-mandat-form#remoteConstentMethodChanged",
                "data-new-mandat-form-target": "remoteConstentMethodInput",
            },
        )
        form.widget_attrs(
            "user_phone",
            {"data-new-mandat-form-target": "userPhoneInput"},
        )

        return form

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "sms_method_value": RemoteConsentMethodChoices.SMS.name,
        }


class RemoteMandateMixin:
    waiting_room_path = "new_mandat_waiting_room"
    mandat_form_path = "new_mandat"

    """Processes remote consent

    How to add a new remote consent method
    ======================================

    You'll need to create 3 new methods:
    - ``_process_{method}_first_step``
    - ``_process_{method}_second_step``
    - ``_process_{method}_consent_validation``

    where ``{method}`` corresponds to a lowercase value from
    ``RemoteConsentMethodChoices``.

    Each method is responsible for validating that the previous steps happened, for
    instance, by validating that a ``Journal`` was created for that step, and return
    an `HttpResponse` otherwise.

    ``None`` must be returned if the step was correctly processed (an SMS was sent,
    the consent was correctly received, etc.)

    ``_process_{method}_first_step`` is responsible for notifying the user with the
    caracteristics of the mandate (duration, scopes,etc.)

    ``_process_{method}_second_step`` is reponsible for asking the user for their
    consent.

    ``_process_{method}_consent_validation`` is responsible for checking that the user
    has consented (for instance, searching through the ``Journal``s).
    """

    def process_consent_first_step(
        self, aidant: Aidant, organisation: Organisation, form: MandatForm
    ) -> None | HttpResponse:
        if (
            not form.cleaned_data["is_remote"]
            or form.cleaned_data["remote_constent_method"]
            not in RemoteConsentMethodChoices.blocked_methods()
        ):
            return None
        method = str(form.cleaned_data["remote_constent_method"]).lower()
        process: Callable[
            [Aidant, Organisation, MandatForm], None | HttpResponse
        ] = getattr(
            self,
            f"_process_{method}_first_step",
            self._process_unknown_first_step,
        )
        return process(aidant, organisation, form)

    def process_consent_second_step(
        self, connection: Connection
    ) -> None | HttpResponse:
        if (
            not connection.mandat_is_remote
            or connection.remote_constent_method
            not in RemoteConsentMethodChoices.blocked_methods()
        ):
            return None

        method = str(connection.remote_constent_method).lower()
        process: Callable[[Connection], None | HttpResponse] = getattr(
            self, f"_process_{method}_second_step", self._process_unknown
        )
        return process(connection)

    def process_consent_validation(self, connection: Connection) -> None | HttpResponse:
        if (
            not connection.mandat_is_remote
            or connection.remote_constent_method
            not in RemoteConsentMethodChoices.blocked_methods()
        ):
            return None

        method = str(connection.remote_constent_method).lower()
        process: Callable[[Connection], None | HttpResponse] = getattr(
            self, f"_process_{method}_consent_validation", self._process_unknown
        )
        return process(connection)

    def _process_sms_first_step(
        self, aidant: Aidant, organisation: Organisation, form: MandatForm
    ) -> None | HttpResponse:
        data = form.cleaned_data
        user_phone: PhoneNumber = data["user_phone"]

        self.consent_request_id = str(uuid4())

        # Try to choose another UUID if there's already one
        # associated with this number in DB.
        while Journal.objects.find_sms_consent_requests(
            user_phone, self.consent_request_id
        ).exists():
            self.consent_request_id = str(uuid4())

        message = render_to_string(
            "aidants_connect_web/sms/pre-consent-recap.txt",
            context={
                "aidant": aidant,
                "organisation": organisation,
                "demarches": [
                    settings.DEMARCHES[demarche]["titre"].capitalize()
                    for demarche in sorted(form.cleaned_data["demarche"])
                ],
                "duree_text": AuthorizationDurationChoices(
                    form.cleaned_data["duree"]
                ).label,
            },
        )

        # Strip the traling spaces
        message = re.sub(r"(^\s*)|(\s*$)", "", message)

        try:
            SmsApi().send_sms(user_phone, self.consent_request_id, message)
        except SmsApi.HttpRequestExpection:
            log.exception(
                "An error happend while trying to send the mandate recap by SMS"
            )
            error_datetime = timezone.now()
            email_body = render_to_string(
                "aidants_connect_web/sms/support_email_send_failure_body.txt",
                context={
                    "datetime": error_datetime,
                    "number": str(user_phone),
                    "consent_request_id": self.consent_request_id,
                },
            )
            django_messages.error(
                self.request,
                format_html(
                    "Une erreur est survenue pendant l'envoi du SMS de "
                    "récapitulatif. Merci de réessayer plus tard. Si l'erreur "
                    "persiste, merci de nous la signaler {}.",
                    mailto(
                        "en suivant ce lien pour nous envoyer un email",
                        settings.SMS_SUPPORT_EMAIL,
                        settings.SMS_SUPPORT_EMAIL_SEND_FAILURE_SUBJET,
                        email_body,
                    ),
                ),
            )
            return redirect("espace_aidant_home")

        Journal.log_user_mandate_recap_sms_sent(
            aidant=aidant,
            demarche=data["demarche"],
            duree=data["duree"],
            remote_constent_method=data["remote_constent_method"],
            user_phone=user_phone,
            consent_request_id=self.consent_request_id,
            message=message,
        )

    def _process_sms_second_step(self, connection: Connection):
        if not Journal.objects.find_sms_consent_recap(
            connection.user_phone, connection.consent_request_id
        ).exists():
            # First step not performed
            django_messages.error(
                self.request,
                "Le récapitulatif de de mandat n'a pas été envoyé. "
                "Veuillez réitérer l'opération de création de mandat.",
            )
            return redirect(self.mandat_form_path)

        message = render_to_string(
            "aidants_connect_web/sms/consent_request.txt",
            context={"sms_response_consent": settings.SMS_RESPONSE_CONSENT},
        )
        message = re.sub(r"(^\s*)|(\s*$)", "", message)

        try:
            SmsApi().send_sms(
                connection.user_phone, connection.consent_request_id, message
            )
        except SmsApi.HttpRequestExpection:
            log.exception(
                "An error happend while trying to send an SMS consent request"
            )
            error_datetime = timezone.now()
            email_body = render_to_string(
                "aidants_connect_web/sms/support_email_send_failure_body.txt",
                context={
                    "datetime": error_datetime,
                    "number": str(connection.user_phone),
                    "consent_request_id": connection.consent_request_id,
                },
            )
            django_messages.error(
                self.request,
                format_html(
                    "Une erreur est survenue pendant l'envoi du SMS de "
                    "consentement. Merci de réessayer plus tard. Si l'erreur persiste, "
                    "merci de nous la signaler {}.",
                    mailto(
                        "en suivant ce lien pour nous envoyer un email",
                        settings.SMS_SUPPORT_EMAIL,
                        settings.SMS_SUPPORT_EMAIL_SEND_FAILURE_SUBJET,
                        email_body,
                    ),
                ),
            )
            return redirect("espace_aidant_home")

        Journal.log_user_consent_request_sms_sent(
            aidant=connection.aidant,
            demarche=connection.demarche,
            duree=AuthorizationDurations.duration(connection.duree_keyword),
            remote_constent_method=connection.remote_constent_method,
            user_phone=connection.user_phone,
            consent_request_id=connection.consent_request_id,
            message=message,
        )

    def _process_sms_consent_validation(self, connection: Connection):
        if not Journal.objects.find_sms_user_consent(
            connection.user_phone, connection.consent_request_id
        ).exists():
            django_messages.warning(
                self.request,
                "La personne accompagnée n'a pas encore donné "
                "son consentement pour la création du mandat.",
            )

            return redirect(self.waiting_room_path)

    def _process_unknown_first_step(
        self,
        aidant: Aidant,
        organisation: Organisation,
        form: MandatForm,
    ):
        log.error(f"Unknown remote consent method {form['remote_constent_method']}")
        raise Http404()

    def _process_unknown(
        self,
        connection: Connection,
    ):
        log.error(f"Unknown remote consent method {connection.remote_constent_method}")
        raise Http404()


class RenderAttestationAbstract(TemplateView):
    template_name = "aidants_connect_web/attestation.html"
    final = False
    modified = False

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "usager": self.get_usager(),
            "aidant": self.request.user,
            "date": formats.date_format(self.get_date(), "l j F Y"),
            "demarches": [
                humanize_demarche_names(demarche) for demarche in self.get_demarches()
            ],
            "duree": self.get_duree(),
            "current_mandat_template": self.get_template(),
            "final": self.final,
            "modified": self.modified,
        }

    def get_usager(self) -> Usager:
        raise NotImplementedError()

    def get_date(self) -> date:
        raise NotImplementedError()

    def get_demarches(self) -> List[str]:
        raise NotImplementedError()

    def get_duree(self) -> str:
        raise NotImplementedError()

    def get_template(self) -> str:
        raise NotImplementedError()


@aidant_logged_with_activity_required
class NewMandat(RemoteMandateMixin, MandatCreationJsFormView):
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
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "has_mandate_translations": (
                settings.FF_MANDATE_TRANSLATION and MandateTranslation.objects.exists()
            ),
        }

    def get_initial(self):
        return (
            {}
            if self.connection is None
            else {
                "duree": self.connection.duree_keyword,
                "is_remote": self.connection.mandat_is_remote,
                "demarche": self.connection.demarches,
                "user_phone": self.connection.user_phone,
                "remote_constent_method": self.connection.remote_constent_method,
            }
        )

    def get_success_url(self):
        return (
            reverse("fc_authorize")
            if self.connection.remote_constent_method
            not in RemoteConsentMethodChoices.blocked_methods()
            else reverse("new_mandat_remote_second_step")
        )

    def form_valid(self, form: MandatForm):
        data = form.cleaned_data
        self.consent_request_id = ""

        if isinstance(
            result := self.process_consent_first_step(
                self.aidant, self.aidant.organisation, form
            ),
            HttpResponse,
        ):
            return result

        self.connection = Connection.objects.create(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            demarches=data["demarche"],
            duree_keyword=data["duree"],
            mandat_is_remote=data["is_remote"],
            remote_constent_method=data["remote_constent_method"],
            user_phone=data["user_phone"],
            consent_request_id=self.consent_request_id,
        )

        self.request.session["connection"] = self.connection.pk

        return super().form_valid(form)


@aidant_logged_with_activity_required
class RemoteConsentSecondStepView(RemoteMandateMixin, RequireConnectionMixin, FormView):
    template_name = "aidants_connect_web/sms/remote_consent_second_step.html"
    success_url = reverse_lazy("new_mandat_waiting_room")
    form_class = IdentityVerificationForm

    def dispatch(self, request, *args, **kwargs):
        if isinstance(
            result := self.check_connection(request),
            HttpResponse,
        ):
            return result

        self.connection = result

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if isinstance(
            result := self.process_consent_second_step(self.connection),
            HttpResponse,
        ):
            return result

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "duree": self.connection.duree_keyword,
            "demarches": {
                settings.DEMARCHES[name]["titre"]: (
                    settings.DEMARCHES[name]["description"]
                )
                for name in self.connection.demarches
            },
            "user_phone": self.connection.user_phone,
            "aidant": self.connection.aidant,
        }


@aidant_logged_with_activity_required
class NewMandatRecap(RemoteMandateMixin, RequireConnectionMixin, FormView):
    form_class = RecapMandatForm
    template_name = "aidants_connect_web/new_mandat/new_mandat_recap.html"

    def dispatch(self, request, *args, **kwargs):
        if isinstance(result := self.check_connection(request), HttpResponse):
            return result

        self.connection: Connection = result
        self.aidant: Aidant = request.user

        if isinstance(
            result := self.process_consent_validation(self.connection),
            HttpResponse,
        ):
            return result

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        try:
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
        except TypeError as e:
            raise Exception(
                f"Exception from connection with id {self.connection.pk}"
            ) from e

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
                expiration_date=expiration_date,
                is_remote=self.connection.mandat_is_remote,
                remote_constent_method=self.connection.remote_constent_method,
                consent_request_id=self.connection.consent_request_id,
            )

            # Add a Journal 'create_attestation' action
            Journal.log_attestation_creation(
                aidant=self.aidant,
                usager=self.connection.usager,
                demarches=self.connection.demarches,
                is_remote_mandat=self.connection.mandat_is_remote,
                user_phone=self.connection.user_phone,
                remote_constent_method=self.connection.remote_constent_method,
                consent_request_id=self.connection.consent_request_id,
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
class NewMandateSuccess(RequireConnectionView, TemplateView):
    template_name = "aidants_connect_web/new_mandat/new_mandat_success.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
            "usager": self.connection.usager,
        }


@aidant_logged_with_activity_required
class AttestationProject(RequireConnectionView, RenderAttestationAbstract):
    # We don't need to check connection expiration here
    # since we're already after AC connection
    check_connection_expiration = False

    def get_context_data(self, **kwargs):
        try:
            return super().get_context_data(**kwargs)
        except TypeError as e:
            raise Exception(
                f"Exception from connection with id {self.connection.pk}"
            ) from e

    def get_usager(self) -> Usager:
        return self.connection.usager

    def get_date(self) -> date:
        return date.today()

    def get_demarches(self) -> List[str]:
        return self.connection.demarches

    def get_duree(self) -> str:
        return self.connection.get_duree_keyword_display()

    def get_template(self) -> str:
        return settings.MANDAT_TEMPLATE_PATH


@aidant_logged_with_activity_required(more_decorators=[csrf_exempt])
class Translation(RenderAttestationAbstract):
    template_name = "aidants_connect_web/attestation_translation.html"

    def post(self, request, *args, **kwargs):
        lang: MandateTranslation = get_object_or_404(
            MandateTranslation, pk=request.POST.get("lang_code")
        )

        template_engine = next(
            engine for engine in engines.all() if isinstance(engine, DjangoTemplates)
        )

        return self.response_class(
            request=self.request,
            template=template_engine.from_string(lang.to_html()),
            context={},
            using=template_engine,
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "available_translations": MandateTranslation.objects.all(),
        }

    def get_usager(self) -> Usager:
        def not_implemented(*args, **kwargs):
            pass

        user = Usager(
            pk=-100,
            given_name="__________",
            family_name="__________",
            preferred_username="__________",
        )

        user.save = not_implemented  # Prevent saving this object
        return user

    def get_date(self) -> date:
        return date.today()

    def get_demarches(self) -> List[str]:
        return settings.DEMARCHES.keys()

    def get_duree(self) -> str:
        return "__________"

    def get_template(self) -> str:
        return settings.MANDAT_TEMPLATE_PATH


# @aidant_logged_with_activity_required is already on AttestationProject
class AttestationFinal(AttestationProject):
    final = True


@aidant_logged_with_activity_required
class AttestationVisualisation(RenderAttestationAbstract):
    final = True

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        self.mandat = get_object_or_404(
            Mandat, pk=kwargs["mandat_id"], organisation=self.aidant.organisation
        )
        self.template = self.mandat.get_mandate_template_path()
        if self.template:
            # At this point, the generated QR code on the mandate comes from an
            # independant HTTP request. Normally, what we should do is to modifiy how
            # this HTTP request is done so that the mandate ID is passed during the
            # request. But the mandate template can't be modified anymore because that
            # would change their hash and defeat the algorithm that recovers the
            # original mandate template from the journal entries. The only found
            # solution, which is not nice, is to retain the mandate ID as a session
            # state. Please forgive us for what we did...
            request.session["qr_code_mandat_id"] = kwargs["mandat_id"]
        else:
            self.modified = True

        return super().dispatch(request, *args, **kwargs)

    def get_usager(self) -> Usager:
        return self.mandat.usager

    def get_date(self) -> date:
        return self.mandat.creation_date.date()

    def get_demarches(self) -> List[str]:
        return [it.demarche for it in self.mandat.autorisations.all()]

    def get_duree(self) -> str:
        return self.mandat.get_duree_keyword_display()

    def get_template(self) -> str:
        return self.template or settings.MANDAT_TEMPLATE_PATH


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


@aidant_logged_with_activity_required
class WaitingRoom(RequireConnectionView, TemplateView):
    template_name = "aidants_connect_web/sms/remote_consent_waiting_room.html"
    poll_route_name = "new_mandat_waiting_room_json"
    next_route_name = "fc_authorize"

    def get_context_data(self, **kwargs):
        return {
            "next": reverse(self.next_route_name),
            "poll": reverse(self.poll_route_name),
            **super().get_context_data(**kwargs),
        }

    def get(self, request, *args, **kwargs):
        if (
            not self.connection.mandat_is_remote
            or Journal.objects.find_sms_user_consent(
                self.connection.user_phone, self.connection.consent_request_id
            ).exists()
        ):
            return redirect(reverse(self.next_route_name))
        return super().get(request, *args, **kwargs)


@aidant_logged_with_activity_required
class WaitingRoomJson(RequireConnectionView, View):
    def post(self, request, *args, **kwargs):
        if (
            not self.connection.mandat_is_remote
            or Journal.objects.find_sms_user_consent(
                self.connection.user_phone, self.connection.consent_request_id
            ).exists()
        ):
            return JsonResponse({"connectionStatus": "OK"})

        return JsonResponse({"connectionStatus": "NOK"})


@aidant_logged_with_activity_required
class ClearConnectionView(RedirectView):
    def dispatch(self, request, *args, **kwargs):
        request.session.pop("connection", None)
        request.session.pop("qr_code_mandat_id", None)
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        next_path = self.request.GET.get("next", reverse("espace_aidant_home"))
        return unquote_plus(next_path)
