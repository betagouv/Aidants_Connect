import logging

from django.shortcuts import redirect
from django.views import View

from aidants_connect_web.models import Aidant, Connection

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class RequireConnectionObjectMixin(View):
    def dispatch(self, request, *args, **kwargs):
        connection_id = request.session.get("connection")

        if not connection_id:
            log.error("No connection id found in session")
            return redirect("espace_aidant_home")

        self.connection: Connection = Connection.objects.get(pk=connection_id)
        self.aidant: Aidant = request.user

        return super().dispatch(request, *args, **kwargs)
