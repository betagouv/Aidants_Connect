import logging
from secrets import token_urlsafe
from typing import Callable
from uuid import uuid4

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from phonenumbers import PhoneNumber

from aidants_connect_common.templatetags.ac_common import mailto
from aidants_connect_common.utils.constants import AuthorizationDurations
from aidants_connect_common.utils.sms_api import SmsApi
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.decorators import aidant_logged_with_activity_required
from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Aidant, Connection, Journal, Mandat, Usager
from aidants_connect_web.views.mandat import MandatCreationJsFormView
from aidants_connect_web.views.mandat import WaitingRoom as MandatWaitingRoom

logger = logging.getLogger()


@aidant_logged_with_activity_required
class RenewMandat(MandatCreationJsFormView):
    form_class = MandatForm
    template_name = "aidants_connect_web/new_mandat/renew_mandat.html"

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        self.usager: Usager = self.aidant.get_usager(kwargs.get("usager_id"))

        if not Mandat.objects.for_usager(self.usager).renewable().exists():
            django_messages.error(request, "Cet usager n'a aucun mandat renouvelable.")
            return redirect("espace_aidant_home")

        if not self.usager:
            django_messages.error(
                request, "Cet usager est introuvable ou inaccessible."
            )
            return redirect("espace_aidant_home")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        data = form.cleaned_data
        access_token = make_password(token_urlsafe(64), settings.FC_AS_FI_HASH_SALT)
        self.consent_request_id = ""

        if (
            data["is_remote"]
            and data["remote_constent_method"]
            in RemoteConsentMethodChoices.blocked_methods()
        ):
            # Processes remote blocked method (SMS, email)
            # To add another consent method, add a ``process_x_method``
            # For instance ``process_email_method`` and do what you need to do in it
            method = str(data["remote_constent_method"]).lower()
            process: Callable[[MandatForm], None | HttpResponse] = getattr(
                self, f"process_{method}_method", self.process_unknown_method
            )
            result = process(form)
            if isinstance(result, HttpResponse):
                return result

        self.connection = Connection.objects.create(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            connection_type="FS",
            access_token=access_token,
            usager=self.usager,
            demarches=data["demarche"],
            duree_keyword=data["duree"],
            mandat_is_remote=data["is_remote"],
            remote_constent_method=data["remote_constent_method"],
            user_phone=data["user_phone"],
            consent_request_id=self.consent_request_id,
        )
        duree = AuthorizationDurations.duration(self.connection.duree_keyword)
        Journal.log_init_renew_mandat(
            aidant=self.aidant,
            usager=self.usager,
            access_token=self.connection.access_token,
            demarches=self.connection.demarches,
            duree=duree,
            is_remote_mandat=self.connection.mandat_is_remote,
            remote_constent_method=data["remote_constent_method"],
            user_phone=data["user_phone"],
            consent_request_id=self.consent_request_id,
        )

        self.request.session["connection"] = self.connection.pk

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "aidant": self.aidant}

    def get_success_url(self):
        return (
            reverse("new_mandat_recap")
            if self.connection.remote_constent_method
            not in RemoteConsentMethodChoices.blocked_methods()
            else reverse("renew_mandat_waiting_room")
        )

    def process_sms_method(self, form: MandatForm) -> None | HttpResponse:
        data = form.cleaned_data
        user_phone: PhoneNumber = data["user_phone"]
        self.consent_request_id = str(uuid4())

        # Try to choose another UUID if there's already one
        # associated with this number in DB.
        while Journal.objects.find_sms_consent_requests(
            user_phone, self.consent_request_id
        ).exists():
            self.consent_request_id = str(uuid4())

        user_consent_request_sms_text = render_to_string(
            "aidants_connect_web/sms/consent_request.txt",
            context={"sms_response_consent": settings.SMS_RESPONSE_CONSENT},
        )
        try:
            SmsApi().send_sms(
                user_phone,
                self.consent_request_id,
                user_consent_request_sms_text,
            )
        except SmsApi.HttpRequestExpection:
            logger.exception(
                "An error happend while trying to send an SMS consent request"
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
            aidant=self.aidant,
            demarche=data["demarche"],
            duree=data["duree"],
            remote_constent_method=data["remote_constent_method"],
            user_phone=user_phone,
            consent_request_id=self.consent_request_id,
            message=user_consent_request_sms_text,
        )

    def process_unknown_method(self, form: MandatForm):
        raise NotImplementedError(
            f"Unknown remote consent method {form['remote_constent_method']}"
        )


# MandatWaitingRoom is already decorated with aidant_logged_with_activity_required
class WaitingRoom(MandatWaitingRoom):
    poll_route_name = "renew_mandat_waiting_room_json"
    next_route_name = "new_mandat_recap"
