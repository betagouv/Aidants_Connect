from secrets import token_urlsafe


from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect


from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.forms import MandatForm
from aidants_connect_web.models import Connection, Journal, Aidant, Usager
from aidants_connect.common.constants import AuthorizationDurations


@login_required
@user_is_aidant
@activity_required
def renew_mandat(request, usager_id):
    aidant: Aidant = request.user
    usager: Usager = aidant.get_usager(usager_id)

    if not usager:
        django_messages.error(request, "Cet usager est introuvable ou inaccessible.")
        return redirect("espace_aidant_home")

    form = MandatForm()

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/new_mandat/renew_mandat.html",
            {"aidant": aidant, "form": form},
        )

    else:
        form = MandatForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            access_token = make_password(token_urlsafe(64), settings.FC_AS_FI_HASH_SALT)
            connection = Connection.objects.create(
                aidant=aidant,
                organisation=aidant.organisation,
                connection_type="FS",
                access_token=access_token,
                usager=usager,
                demarches=data["demarche"],
                duree_keyword=data["duree"],
                mandat_is_remote=data["is_remote"],
            )
            duree = AuthorizationDurations.duration(connection.duree_keyword)
            Journal.log_init_renew_mandat(
                aidant=aidant,
                usager=usager,
                demarches=connection.demarches,
                duree=duree,
                is_remote_mandat=connection.mandat_is_remote,
                access_token=connection.access_token,
            )

            request.session["connection"] = connection.pk
            return redirect("new_mandat_recap")
        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/renew_mandat.html",
                {"aidant": aidant, "form": form},
            )
