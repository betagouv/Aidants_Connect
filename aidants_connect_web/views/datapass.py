import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from aidants_connect_web.forms import DatapassForm, DatapassHabilitationForm
from aidants_connect_web.models import (
    HabilitationRequest,
    Organisation,
    OrganisationType,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def check_authorization(request):
    try:
        if request.META["HTTP_AUTHORIZATION"] != f"Bearer {settings.DATAPASS_KEY}":
            log.info("403: Bad authorization header for datapass call")
            return False
    except KeyError:
        log.info("403: No authorization header for datapass call")
        return False
    return True


def get_content(request):
    import json

    try:
        # if post data has json form
        content = json.loads(request.body)
    except json.decoder.JSONDecodeError:
        # if post data has querystring form
        content = request.POST
    return content


def habilitation_already_exists(content):
    if "email" not in content or "data_pass_id" not in content:
        return False
    email = content["email"]
    if email:
        email = email.lower()
    return HabilitationRequest.objects.filter(
        email=email,
        organisation__data_pass_id=content["data_pass_id"],
    )


@csrf_exempt
def organisation_receiver(request):
    if not check_authorization(request):
        return HttpResponseForbidden()

    content = get_content(request)

    form = DatapassForm(data=content)

    if form.is_valid():
        data_pass_id = form.cleaned_data["data_pass_id"]
        if Organisation.objects.filter(data_pass_id=data_pass_id).exists():
            log.warning("Organisation already exists.")
            return HttpResponse(status=200)

        orga_type, _ = OrganisationType.objects.get_or_create(
            name=form.cleaned_data["organization_type"]
        )
        this_organisation = Organisation.objects.create(
            data_pass_id=data_pass_id,
            name=form.cleaned_data["organization_name"],
            siret=form.cleaned_data["organization_siret"],
            zipcode=form.cleaned_data["organization_postal_code"],
            address=form.cleaned_data["organization_address"],
            type=orga_type,
        )

        send_mail(
            subject="Une nouvelle structure",
            message=f"""
                la structure {this_organisation.name} vient
                d'être validée pour avoir des accès à Aidants Connect.
                ###
                Vous pouvez consulter la demande sur :
                https://datapass.api.gouv.fr/aidantsconnect/{form.cleaned_data["data_pass_id"]}
            """,
            from_email=settings.DATAPASS_FROM_EMAIL,
            recipient_list=[settings.DATAPASS_TO_EMAIL],
            fail_silently=False,
        )

        return HttpResponse(status=202)
    for error in form.errors:
        message = f"{error} is invalid in the form @ datapass"
        log.warning(message)
    return HttpResponseBadRequest()


@csrf_exempt
def habilitation_receiver(request):
    if not check_authorization(request):
        return HttpResponseForbidden()

    content = get_content(request)

    if (
        all(value == "" for key, value in content.items() if key != "data_pass_id")
        or len(content) == 1
    ):
        log.warning("Habilitation form is empty.")
        return HttpResponse(status=200)

    if habilitation_already_exists(content):
        log.warning("Habilitation already exists.")
        return HttpResponse(status=200)

    form = DatapassHabilitationForm(data=content)

    if form.is_valid():
        form.save()
        return HttpResponse(status=202)

    for error in form.errors:
        message = f"{error} is invalid in the form @ datapass"
        log.warning(message)
    return HttpResponse(status=200)
