import json
import logging
import re

from django.conf import settings
from django.http import HttpResponse, QueryDict
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from phonenumbers import parse as parse_phone

from aidants_connect_common.utils.sms_api import SmsApi
from aidants_connect_web.models import Journal

logger = logging.getLogger()


@method_decorator([csrf_exempt], name="dispatch")
class Callback(View):
    def dispatch(self, request, *args, **kwargs):
        if self.request.method.lower() == "post":
            try:
                data = json.loads(request.body.decode(settings.DEFAULT_CHARSET))
            except (UnicodeDecodeError, json.JSONDecodeError):
                data = {}

            q_dict: QueryDict = self.request.POST
            q_dict._mutable = True
            for key, value in data.items():
                q_dict[key] = value

            q_dict._mutable = False

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if "originatorAddress" not in self.request.POST:
            # SMS send report
            try:
                # Must not fail
                if self.request.POST.get("errorCode", 0) != 0:
                    error_message = self.request.POST.get("errorMessage")
                    additionnal_infos = (
                        f"Error message returned by SMS provider: {error_message}"
                        if error_message
                        else "No error message returned by SMS provider."
                    )
                    logger.warning(
                        "An error happened while trying to send SMS with ID "
                        f"{self.request.POST['correlationId']!r}. {additionnal_infos}"
                    )
            except Exception:
                logger.exception("Error processing API SMS response")
            return HttpResponse("Status=0")

        api = SmsApi()

        try:
            sms_response = api.process_sms_response(self.request.POST)
            phone_number = parse_phone(sms_response.user_phone)
        except SmsApi.ApiRequestExpection as e:
            logger.warning(f"Bad SMS API callback response: {e.reason}")
            return HttpResponse("Status=0")

        # Security: search for consent request fisrt.
        # That ensures nobody outside from the SMS service tries to force the consent
        # making an HTTP request. The SMS tag is a UUID theorically known only to us
        # and the SMS service so it's practically unguessable. It can serve as an
        # authentication token.
        try:
            consent_request = Journal.objects.find_sms_consent_requests(
                phone_number, sms_response.consent_request_id
            )[0]
        except Journal.DoesNotExist:
            logger.warning(
                f"No consent request found for number {phone_number} "
                f"with id {sms_response.consent_request_id}"
            )
            return HttpResponse("Status=0")

        if Journal.objects.find_sms_user_consent_or_denial(
            phone_number, sms_response.consent_request_id
        ).exists():
            logger.warning(
                f"Response already exists for {phone_number} "
                f"with id {sms_response.consent_request_id}"
            )
            return HttpResponse("Status=0")

        kwargs = {
            "aidant": consent_request.aidant,
            "demarche": consent_request.demarche,
            "duree": consent_request.duree,
            "remote_constent_method": consent_request.remote_constent_method,
            "user_phone": consent_request.user_phone,
            "consent_request_id": consent_request.consent_request_id,
            "message": sms_response.message,
        }

        if not self._check_user_consents(sms_response.message):  # No consent case
            Journal.log_user_denies_sms(**kwargs)
            api.send_sms(
                consent_request.user_phone,
                sms_response.consent_request_id,
                render_to_string("aidants_connect_web/sms/denial_receipt.txt"),
            )
        else:
            Journal.log_user_consents_sms(**kwargs)
            api.send_sms(
                consent_request.user_phone,
                sms_response.consent_request_id,
                render_to_string("aidants_connect_web/sms/agreement_receipt.txt"),
            )

        return HttpResponse("Status=0")

    def get(self, request, *args, **kwargs):
        return HttpResponse("Status=0")

    def _check_user_consents(self, user_response: str) -> bool:
        """
        Matches user response against parametered consent response.

        User response will be trimmed and any existing period, removed
        :returns: True if user response matches the parametered consent response,
                  False otherwise.
        """
        # Regex to strip spaces and remove possible final period.
        # Test on https://regex101.com/ for explanation
        actual_response = re.sub(r"(^\s*)|(\s*\.?\s*$)", "", user_response).lower()
        expected_response = settings.SMS_RESPONSE_CONSENT.lower().strip()
        return actual_response == expected_response
