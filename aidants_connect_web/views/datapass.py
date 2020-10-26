import logging

from django.http import HttpResponse, HttpResponseForbidden

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def receiver(request):

    if request.META["HTTP_AUTHORIZATION"] != settings.DATAPASS_KEY:
        log.info("403: Bad authorization header for datapass call")
        return HttpResponseForbidden()
    return HttpResponse(status=202)
