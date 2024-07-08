import inspect
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import starmap
from pathlib import Path

from django.conf import settings
from django.utils.functional import classproperty
from django.utils.timezone import now

from phonenumbers import PhoneNumber, PhoneNumberFormat, format_number
from redis import Redis
from redis.exceptions import ConnectionError
from requests import Session
from requests import post as requests_post
from requests.adapters import HTTPAdapter, Response
from requests.models import PreparedRequest

__all__ = ["SmsApi", "SmsResponseCallbackInfos"]

from . import DateTimeJsonEncoder, join_url_parts

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

    def process_sms_response(self, data: dict) -> SmsResponseCallbackInfos:
        """Takes the JSON body of the callback as **kwargs"""
        raise NotImplementedError()


class SmsApiMock(SmsApi):
    def __init__(self, message):
        self._message = message

    def send_sms(self, phone: PhoneNumber, consent_request_id: str, message: str):
        if settings.DEBUG and getattr(settings, "EMAIL_FILE_PATH", None):
            file = Path(settings.EMAIL_FILE_PATH).resolve()
            file.mkdir(parents=True, exist_ok=True)
            file = file / f"{now().strftime('%Y%m%d-%H%M%S')}-{abs(id(self))}.log"
            formatted_phone = format_number(phone, PhoneNumberFormat.INTERNATIONAL)
            with open(file, "a") as f:
                f.writelines(
                    [
                        f"Téléphone : {formatted_phone}\n",
                        f"ID de requête : {consent_request_id}\n\n",
                        message,
                    ]
                )
        else:
            self._log_message()

    def process_sms_response(self, data: dict) -> SmsResponseCallbackInfos:
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

        self._snd_sms_url = join_url_parts(
            self._base_url, settings.LM_SMS_SERVICE_SND_SMS_ENDPOINT
        )

        self._auth_infos = AuthInfos(
            settings.LM_SMS_SERVICE_USERNAME,
            settings.LM_SMS_SERVICE_PASSWORD,
            join_url_parts(self._base_url, settings.LM_SMS_SERVICE_OAUTH2_ENDPOINT),
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

    def send_sms(self, phone: PhoneNumber, consent_request_id: str, message: str):
        phone = format_number(phone, PhoneNumberFormat.E164).removeprefix("+")

        response = self._client.post(
            self._snd_sms_url,
            json={
                "userIds": [phone],
                "correlationId": consent_request_id,
                "message": message.strip(),
                "encoding": "Unicode",
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

    def process_sms_response(self, data: dict) -> SmsResponseCallbackInfos:
        try:
            init_kwargs = {
                "user_phone": f"+{data['originatorAddress'].removeprefix('+')}",
                "message": data["message"].strip(),
                "consent_request_id": data["smsMTCorrelationId"],
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
        return self.emitted + timedelta(seconds=self.ttl) <= now()

    def as_json_string(self):
        return DateTimeJsonEncoder().encode(self.__dict__)

    @staticmethod
    def from_json(json_dict):
        try:
            emitted = (
                datetime.fromisoformat(json_dict["emitted"])
                if "emitted" in json_dict
                else now()
            )
        except Exception:
            logger.exception("Error creating TokenInfos")
            emitted = now()

        return TokenInfos(
            access_token=json_dict["access_token"],
            ttl=int(json_dict["ttl"]),
            emitted=emitted,
        )


class OAuthClient(Session):
    def __init__(self, auth_infos: AuthInfos) -> None:
        super().__init__()
        self.mount("https://", OAuthMiddleware(auth_infos))
        self.mount("http://", OAuthMiddleware(auth_infos))


class OAuthMiddleware(HTTPAdapter):
    _token: None | TokenInfos = None
    __attrs__ = [*HTTPAdapter.__attrs__, "_auth_infos"]

    @classproperty
    def redis_client(cls):
        if not hasattr(cls, "_redis_client"):
            cls._redis_client = Redis.from_url(settings.REDIS_URL)
            try:
                cls._redis_client.ping()
            except ConnectionError:
                logger.warning(f"{__file__}: No Redis connection available")
                cls._redis_client = None
        return cls._redis_client

    @property
    def token(self):
        if isinstance(self._token, TokenInfos):
            return self._token

        if self.redis_client:
            try:
                if token := self.redis_client.get(__name__):
                    self._token = TokenInfos.from_json(json.loads(token))
                    return self._token
            except Exception:
                logger.exception("Error retreiving token from Redis")

        return None

    @token.setter
    def token(self, value: TokenInfos):
        self._token = value

        if self.redis_client:
            try:
                self.redis_client.set(
                    __name__,
                    value.as_json_string(),
                    # Expire data in redis 10 minute sooner
                    # to avoid falling outside the TTL
                    keepttl=(value.ttl - 10 if value.ttl > 10 else value.ttl),
                )
            except Exception:
                logger.exception("Error setting token in Redis")

    def __init__(self, auth_infos: AuthInfos, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._auth_infos = auth_infos

    def send(self, request: PreparedRequest, *args, **kwargs) -> Response:
        # Case of a request for the token URL; does not require authentication
        # We directly send the request without fetching a token first
        # (this would result in a loop!)
        if request.url.startswith(self._auth_infos.access_token_url):
            return super().send(request, *args, **kwargs)

        if not self.token or self.token.is_expired():
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

        self.token = TokenInfos.from_json(response)

    def _send(self, request: PreparedRequest, *args, **kwargs):
        request.headers["Content-Type"] = "application/json"
        request.headers["Authorization"] = f"Bearer {self._token.access_token}"
        return super().send(request, *args, **kwargs)
