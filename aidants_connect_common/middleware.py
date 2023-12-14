import contextlib
from datetime import datetime, timedelta
from logging import getLogger

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils.timezone import now

from django_blocklist.utils import add_to_blocklist, user_ip_from_request
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = getLogger(__name__)


class ThrottleIPMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_client: Redis = Redis.from_url(settings.REDIS_URL)

    def __call__(self, request):
        if settings.DEBUG:
            return self.get_response(request)

        try:
            self.redis_client.ping()
        except RedisConnectionError:
            return self.get_response(request)

        ip = user_ip_from_request(request)

        # Debounce requests to prevent bots from hammering the DB
        # We don't want the debouncer to crash the app
        with contextlib.suppress(Exception):
            result = self.redis_client.set(
                f"last_seen:{ip}",
                now().isoformat(),
                get=True,
                nx=True,
                px=settings.BLOCKLIST_THROTTLE_MS,
            )
            if result is not None:
                last_seen = datetime.fromisoformat(result.decode("utf-8"))
                current_time = now()
                if last_seen > current_time - timedelta(
                    milliseconds=settings.BLOCKLIST_THROTTLE_MS
                ):
                    elapsed = (current_time - last_seen).microseconds / 1000
                    logger.warning(
                        f"Throttling request from IP {ip}: 2 requests in {elapsed}ms"
                    )
                    return HttpResponseBadRequest()
                else:
                    self.redis_client.set(
                        f"last_seen:{ip}",
                        now().isoformat(),
                        px=settings.BLOCKLIST_THROTTLE_MS,
                    )

        response = self.get_response(request)

        if response.status_code == 404:
            self.redis_client.setnx(ip, "0")
            num_fail = int(self.redis_client.incr(ip))
            self.redis_client.expire(ip, settings.BLOCKLIST_EXPIRE_SECONDS)

            if num_fail >= settings.BLOCKLIST_REQUEST_THRESHOLD:
                add_to_blocklist({ip})

        return response
