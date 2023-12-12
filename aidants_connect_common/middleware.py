from django.conf import settings

from django_blocklist.utils import add_to_blocklist, user_ip_from_request
from redis import Redis


class ThrottleIPMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_client: Redis = Redis.from_url(settings.REDIS_URL)

    def __call__(self, request):
        if settings.DEBUG:
            return self.get_response(request)

        response = self.get_response(request)

        try:
            self.redis_client.ping()
        except ConnectionError:
            return response

        if response.status_code == 404:
            ip = user_ip_from_request(request)
            self.redis_client.setnx(ip, "0")
            num_fail = int(self.redis_client.incr(ip))
            self.redis_client.expire(ip, settings.BLOCKLIST_THROTTLE_SECONDS)

            if num_fail >= settings.BLOCKLIST_THROTTLE_THRESHOLD:
                add_to_blocklist({ip})

        return response
