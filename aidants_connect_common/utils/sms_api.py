import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import starmap

from django.conf import settings
from django.utils.timezone import now

from phonenumbers import PhoneNumber
from requests import Session
from requests import post as requests_post
from requests.adapters import HTTPAdapter, Response
from requests.models import PreparedRequest

__all__ = ["SmsApi", "SmsResponseCallbackInfos"]

logger = logging.getLogger()


@dataclass
class SmsResponseCallbackInfos:
    user_phone: str
    message: str
    consent_request_id: str


class SmsApiFactory(type):
    def __call__(cls, *args, **kwds) -> "SmsApi":
        if settings.SMS_API_DISABLED:
            instance: SmsApiMock = object.__new__(SmsApiMock)
            instance.__init__(
                "SMS API is explicitely disabled by environment "
                "variable SMS_API_DISABLED."
            )
            return instance
        elif lm_settings := [
            setting
            for setting in dir(settings)
            if setting.startswith("LM_") and not f"{getattr(settings, setting)}".strip()
        ]:
            only_one = len(lm_settings) == 1
            message = (
                "SMS API is disabled because environment variable {} is not set."
                if only_one
                else "SMS API is disabled because environment variables {} are not set."
            ).format(lm_settings[0] if only_one else f"{lm_settings!r}")

            instance: SmsApiMock = object.__new__(SmsApiMock)
            instance.__init__(message)
            return instance
        else:
            instance: SmsApiImpl = object.__new__(SmsApiImpl)
            instance.__init__()
            return instance


class SmsApi(metaclass=SmsApiFactory):
    """
    Our SMS provider's API endpoints are not OK to publish in
    our settings.py so we need to check on init that these settings
    exists and return something that won't crash but correclty
    advertise that something's wrong
    """

    class HttpRequestExpection(Exception):
        def __init__(self, code: int, reason: str):
            self.code = code
            self.reason = reason
            super().__init__(f"{self.__class__.__qualname__} {code}: {reason}")

    class ApiRequestExpection(HttpRequestExpection):
        pass

    def send_sms(self, phone: PhoneNumber, consent_request_id: str, message: str):
        raise NotImplementedError()

    def process_sms_response(self, **kwargs) -> SmsResponseCallbackInfos:
        """Takes the JSON body of the callback as **kwargs"""
        raise NotImplementedError()


class SmsApiMock(SmsApi):
    def __init__(self, message):
        self._message = message

    def send_sms(self, phone: PhoneNumber, consent_request_id: str, message: str):
        self._log_message()

    def process_sms_response(self, **kwargs) -> SmsResponseCallbackInfos:
        self._log_message()
        return SmsResponseCallbackInfos("", "", "")

    def _log_message(self):
        fun_name = inspect.stack()[1].function
        logger.error(
            f"{self.__class__.__qualname__}.{fun_name}(): "
            f"SMS API is not available; reason: {self._message}"
        )


class SmsApiImpl(SmsApi):
    """
    Main class for manipulating the SMS API.

    The SMS API uses an OAuth2 authentication with legacy flow
    (username/password).
    """

    def __init__(self):
        self._base_url = settings.LM_SMS_SERVICE_BASE_URL

        self._snd_sms_url = self._join_url_parts(
            self._base_url, settings.LM_SMS_SERVICE_SND_SMS_ENDPOINT
        )

        self._auth_infos = AuthInfos(
            settings.LM_SMS_SERVICE_USERNAME,
            settings.LM_SMS_SERVICE_PASSWORD,
            self._join_url_parts(
                self._base_url, settings.LM_SMS_SERVICE_OAUTH2_ENDPOINT
            ),
        )

        self._client = OAuthClient(self._auth_infos)

    def __str__(self):
        props = [
            ("base_url", self._base_url),
            ("auth_infos", self._auth_infos),
        ]

        return (
            f"{self.__class__.__qualname__}"
            f"({','.join(starmap(lambda k, v: f'{k}={v!r}', props))})"
        )

    def _join_url_parts(self, base: str, *args):
        parts = "/".join([arg.removeprefix("/").removesuffix("/") for arg in args])
        return f"{base.removesuffix('/')}/{parts}"

    def send_sms(self, phone: PhoneNumber, consent_request_id: str, message: str):
        phone = str(phone).removeprefix("+")

        response = self._client.post(
            self._snd_sms_url,
            json={
                "userIds": [phone],
                "correlationId": consent_request_id,
                "message": message.strip(),
            },
        )

        if not f"{response.status_code}".startswith("20"):
            raise SmsApi.HttpRequestExpection(
                response.status_code, response.reason
            ) from None

        response = response.json()
        if response.get("errorReason"):
            raise SmsApi.ApiRequestExpection(
                response["errorReason"],
                response.get("errorMessage", "No message given by SMS provider"),
            ) from None

    def process_sms_response(self, **kwargs) -> SmsResponseCallbackInfos:
        try:
            init_kwargs = {
                "user_phone": f"+{kwargs['originatorAddress'].removeprefix('+')}",
                "message": kwargs["message"].strip(),
                "consent_request_id": kwargs["smsMTCorrelationId"],
            }

            return SmsResponseCallbackInfos(**init_kwargs)
        except KeyError as e:
            raise SmsApi.ApiRequestExpection(
                0, f"{e.args[0]} not present in JSON response"
            ) from None


@dataclass
class AuthInfos:
    username: str
    password: str
    access_token_url: str

    def __repr__(self):
        props = [
            f"{k}=********" if v == self.password else f"{k}={v!r}"
            for k, v in self.__dict__.items()
        ]
        return f"{self.__class__.__qualname__}({','.join(props)})"


@dataclass
class TokenInfos:
    access_token: str
    ttl: int
    emitted: datetime = field(default_factory=now)

    def is_expired(self):
        return self.emitted + timedelta(seconds=self.ttl) < now()

    @staticmethod
    def from_json(json):
        return TokenInfos(access_token=json["access_token"], ttl=json["ttl"])


class OAuthClient(Session):
    def __init__(self, auth_infos: AuthInfos) -> None:
        super().__init__()
        self.mount("https://", OAuthMiddleware(auth_infos))
        self.mount("http://", OAuthMiddleware(auth_infos))


class OAuthMiddleware(HTTPAdapter):
    _token: None | TokenInfos = None
    __attrs__ = [*HTTPAdapter.__attrs__, "_auth_infos"]

    def __init__(self, auth_infos: AuthInfos, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._auth_infos = auth_infos

    def send(self, request: PreparedRequest, *args, **kwargs) -> Response:
        # Case of a request for the token URL; does not require authentication
        # We directly send the request without fetching a token first
        # (this would result in a loop!)
        if request.url.startswith(self._auth_infos.access_token_url):
            return super().send(request, *args, **kwargs)

        if not self._token or self._token.is_expired():
            self._fetch_token()

        response = self._send(request, *args, **kwargs)
        if response.status_code != 401:
            return response

        # Unauthorized, token is expired
        self._fetch_token()
        return self._send(request, *args, **kwargs)

    def _fetch_token(self):
        response = requests_post(
            self._auth_infos.access_token_url,
            json={
                "username": self._auth_infos.username,
                "password": self._auth_infos.password,
            },
        ).json()

        self._token = TokenInfos.from_json(response)

    def _send(self, request: PreparedRequest, *args, **kwargs):
        request.headers["Content-Type"] = "application/json"
        request.headers["Authorization"] = f"Bearer {self._token.access_token}"
        return super().send(request, *args, **kwargs)
