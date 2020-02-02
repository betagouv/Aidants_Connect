import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages

from aidants_connect_web.decorators import activity_required
from aidants_connect_web.models import Usager


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@activity_required
def usagers_index(request):
    messages = get_messages(request)
    aidant = request.user
    # TODO: understand why there is a bug if 'usagers' as variable
    aidant_usagers = aidant.get_usagers()

    return render(
        request,
        "aidants_connect_web/usagers.html",
        {"aidant": aidant, "aidant_usagers": aidant_usagers, "messages": messages},
    )


@login_required
@activity_required
def usagers_details(request, usager_id):
    messages = get_messages(request)
    aidant = request.user
    usager = Usager.objects.get(pk=usager_id)
    active_mandats = aidant.get_active_mandats_for_usager(usager_id)
    expired_mandats = aidant.get_expired_mandats_for_usager(usager_id)

    return render(
        request,
        "aidants_connect_web/usagers_details.html",
        {
            "aidant": aidant,
            "usager": usager,
            "active_mandats": active_mandats,
            "expired_mandats": expired_mandats,
            "messages": messages,
        },
    )
