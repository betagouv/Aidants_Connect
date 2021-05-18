from django.urls import reverse
from django.conf import settings

from ovh import Client
from phonenumbers import PhoneNumber, PhoneNumberFormat, format_number

__all__ = ["api", "SafeClient"]


class SafeClient:
    class SmsApiNotEnabledError(Exception):
        def __init__(self):
            super().__init__("Setting OVH_SMS_ENDPOINT is set to false in settings.py")

    def get(self, *args, **kwargs):
        raise SafeClient.SmsApiNotEnabledError()

    def put(self, *args, **kwargs):
        raise SafeClient.SmsApiNotEnabledError()

    def post(self, *args, **kwargs):
        raise SafeClient.SmsApiNotEnabledError()

    def delete(self, *args, **kwargs):
        raise SafeClient.SmsApiNotEnabledError()


class SmsApi:
    """
    For reference:
    OVH SMS documentation: https://eu.api.ovh.com/console/#/sms
    OVH SMS cookbook: https://docs.ovh.com/fr/sms/api_sms_cookbook/
    OVH python module documentation: https://pypi.org/project/ovh/
    """

    def __init__(self):
        self.__client_impl: Client = None

    @property
    def __client(self) -> Client:
        if self.__client_impl is None:
            self.__client_impl = (
                Client(
                    endpoint=settings.OVH_SMS_ENDPOINT,
                    application_key=settings.OVH_SMS_APPLICATION_KEY,
                    application_secret=settings.OVH_SMS_APPLICATION_SECRET,
                    consumer_key=settings.OVH_SMS_CONSUMER_KEY,
                )
                if settings.OVH_SMS_ENABLED
                else SafeClient()
            )
        return self.__client_impl

    def send_sms_for_response(self, tel_num: PhoneNumber, sms_tag: str, message: str):
        """
        Takes a a phone number to which send a consent request and returns the tag of
        the SMS. This tag can be used on the OVH API to uniquely identify a conversation
        with the user. The tag is a generated UUID.
        """

        self.__client.put(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}",
            callBack="",
            stopCallBack="",
            smsResponse={
                "cgiUrl": settings.OVH_SMS_CALLBACK_DOMAIN + reverse("sms_callback"),
                "responseType": "cgi",
            },
        )

        self.__send_sms(tel_num, sms_tag, message, for_response=True)

    def send_simple_sms(self, tel_num: PhoneNumber, sms_tag: str, message: str):
        self.__send_sms(tel_num, sms_tag, message, for_response=False)

    def delete_response(self, sms_id: str):
        return self.__client.delete(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}/incoming/{sms_id}"
        )

    def __send_sms(
        self, tel_num: PhoneNumber, sms_tag: str, message: str, for_response: bool
    ):
        tel_num: str = format_number(tel_num, PhoneNumberFormat.E164)

        result = self.__client.post(
            f"/sms/{settings.OVH_SMS_SERVICE_NAME}/jobs",
            receivers=[tel_num],
            message=message,
            sender=settings.OVH_SMS_SENDER_ID,
            senderForResponse=for_response,
            noStopClause=True,
            tag=sms_tag,
        )

        valid_receivers = result.get("validReceivers", [])

        if not valid_receivers or valid_receivers[0] != tel_num:
            raise Exception("SMS was not sent")


api = SmsApi()
