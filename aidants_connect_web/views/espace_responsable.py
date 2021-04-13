from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from aidants_connect_web.decorators import user_is_responsable_structure


@login_required
@user_is_responsable_structure
def home(request):
    responsable = request.user

    return render(
        request,
        "aidants_connect_web/espace_responsable/home.html",
        {"responsable": responsable},
    )
