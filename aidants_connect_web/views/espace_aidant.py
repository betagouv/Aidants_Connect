from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    aidant = request.user
    messages = django_messages.get_messages(request)
    return render(
        request,
        "aidants_connect_web/espace_aidant/home.html",
        {"aidant": aidant, "messages": messages},
    )


@login_required
def organisation(request):
    aidant = request.user
    messages = django_messages.get_messages(request)
    return render(
        request,
        "aidants_connect_web/espace_aidant/organisation.html",
        {"aidant": aidant, "messages": messages},
    )
