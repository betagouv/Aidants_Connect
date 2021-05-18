from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from phonenumbers import parse as numbers_parse, PhoneNumber

from aidants_connect_web.sms_api import api
from aidants_connect_web.models import Journal


@csrf_exempt
@require_POST
def callback(request):
    # Short tel num that received response
    shortcode: str = request.POST["shortcode"]  # noqa: F841 (ignore unused var)
    sms_tag: str = request.POST["tag"]
    sms_id: str = request.POST["id"]
    user_phone: PhoneNumber = numbers_parse(
        request.POST["senderid"], settings.PHONENUMBER_DEFAULT_REGION
    )
    message: str = request.POST["message"].strip()

    # Security: search for consent request fisrt.
    # That ensures nobody outside from the OVH service tries to force the consent making
    # an HTTP request. The SMS tag is a UUID theorically known only to us and the OVH
    # service so it's practically unguessable. It can serve as an authentication token.
    try:
        consent_request = Journal.find_consent_request(user_phone, sms_tag)
    except Journal.DoesNotExist:
        return HttpResponse()

    # Return directy if agreement or denial already exists.
    if Journal.find_consent_denial_or_agreement(user_phone, sms_tag).count() != 0:
        return HttpResponse()

    try:
        api.delete_response(sms_id)
    except Exception:
        pass

    consent_response = settings.OVH_SMS_RESPONSE_CONSENT.lower().strip()

    kwargs = {
        "aidant": consent_request.aidant,
        "demarche": consent_request.demarche,
        "duree": consent_request.duree,
        "user_phone": consent_request.user_phone,
        "consent_request_tag": consent_request.consent_request_tag,
    }

    if message.lower() != consent_response:  # No consent case
        Journal.log_denial_of_consent_received(**kwargs)
        api.send_simple_sms(
            user_phone,
            sms_tag,
            render_to_string("aidants_connect_web/sms_denial_receipt.txt"),
        )
    else:
        Journal.log_agreement_of_consent_received(**kwargs)
        api.send_simple_sms(
            user_phone,
            sms_tag,
            render_to_string("aidants_connect_web/sms_agreement_receipt.txt"),
        )

    return HttpResponse()
