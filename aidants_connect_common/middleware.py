from datetime import timedelta

from django.conf import settings

from django_blocklist.middleware import BlocklistMiddleware
from django_blocklist.utils import update_blocklist, user_ip_from_request
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError


class SearchEngineIndexingMiddleware:
    """Prevent search engines from indexing non-production environments."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.ALLOW_SEARCH_ENGINE_INDEXING:
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response


class BlocklistMiddleware2(BlocklistMiddleware):
    def __call__(self, request):
        if request.path.startswith(f"/{settings.STATIC_URL.lstrip('/')}"):
            return self.get_response(request)
        return super().__call__(request)


class ThrottleIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_client: Redis = Redis.from_url(settings.REDIS_URL)

    def __call__(self, request):
        response = self.get_response(request)

        if settings.DEBUG:
            return response

        try:
            self.redis_client.ping()
        except RedisConnectionError:
            return response

        ip = user_ip_from_request(request)

        if response.status_code == 404:
            self.redis_client.setnx(ip, "0")
            num_fail = int(self.redis_client.incr(ip))
            self.redis_client.expire(
                ip, timedelta(seconds=settings.BLOCKLIST_EXPIRE_SECONDS)
            )

            if num_fail >= settings.BLOCKLIST_REQUEST_THRESHOLD:
                update_blocklist({ip})

        return response
