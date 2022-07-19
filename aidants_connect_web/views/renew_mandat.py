from secrets import token_urlsafe

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import FormView

from aidants_connect.common.constants import AuthorizationDurations
from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Aidant, Connection, Journal, Usager


class RenewMandat(FormView):
    form_class = MandatForm
    template_name = "aidants_connect_web/new_mandat/renew_mandat.html"

    @method_decorator([login_required, user_is_aidant, activity_required])
    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        self.usager: Usager = self.aidant.get_usager(kwargs.get("usager_id"))

        if not self.usager:
            django_messages.error(
                request, "Cet usager est introuvable ou inaccessible."
            )
            return redirect("espace_aidant_home")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        data = form.cleaned_data
        access_token = make_password(token_urlsafe(64), settings.FC_AS_FI_HASH_SALT)
        connection = Connection.objects.create(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            connection_type="FS",
            access_token=access_token,
            usager=self.usager,
            demarches=data["demarche"],
            duree_keyword=data["duree"],
            mandat_is_remote=data["is_remote"],
        )
        duree = AuthorizationDurations.duration(connection.duree_keyword)
        Journal.log_init_renew_mandat(
            aidant=self.aidant,
            usager=self.usager,
            demarches=connection.demarches,
            duree=duree,
            is_remote_mandat=connection.mandat_is_remote,
            access_token=connection.access_token,
        )

        self.request.session["connection"] = connection.pk

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant,
        }

    def get_success_url(self):
        return reverse("new_mandat_recap")
