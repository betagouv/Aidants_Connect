import logging

from django.conf import settings
from django.http import HttpResponse
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
    def post(self, request, *args, **kwargs):
        api = SmsApi()
        try:
            sms_response = api.process_sms_response(**self.request.POST)
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
        }

        consent_response = settings.SMS_RESPONSE_CONSENT.lower().strip()
        if sms_response.message.lower() != consent_response:  # No consent case
            Journal.log_user_denies_sms(**kwargs)
            api.send_sms(
                consent_request.user_phone,
                sms_response.consent_request_id,
                render_to_string(
                    "aidants_connect_web/new_mandat/sms_denial_receipt.txt"
                ),
            )
        else:
            Journal.log_user_consents_sms(**kwargs)
            api.send_sms(
                consent_request.user_phone,
                sms_response.consent_request_id,
                render_to_string(
                    "aidants_connect_web/new_mandat/sms_agreement_receipt.txt"
                ),
            )

        return HttpResponse("Status=0")
