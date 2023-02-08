import logging

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views import View

from aidants_connect_web.models import Aidant, Connection

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class RequireConnectionMixin:
    def check_connection(self, request: HttpRequest) -> HttpResponse | Connection:
        connection_id = request.session.get("connection")
        view_location = f"{self.__module__}.{self.__class__.__name__}"

        try:
            connection: Connection = Connection.objects.get(pk=connection_id)
            if connection.is_expired:
                log.info(f"Connection has expired @ {view_location}")
                return render(request, "408.html", status=408)

            return connection
        except Exception:
            log.error(
                f"No connection id found for id {connection_id} @ {view_location}"
            )
            logout(request)
            return HttpResponseForbidden()


class RequireConnectionView(RequireConnectionMixin, View):
    def dispatch(self, request, *args, **kwargs):
        result = self.check_connection(request)
        if isinstance(result, HttpResponse):
            return result
        else:
            self.connection = result
        self.aidant: Aidant = request.user
        return super().dispatch(request, *args, **kwargs)
