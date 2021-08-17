import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from aidants_connect_web.forms import DatapassForm
from aidants_connect_web.models import Organisation, OrganisationType

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@csrf_exempt
def receiver(request):
    try:
        if request.META["HTTP_AUTHORIZATION"] != f"Bearer {settings.DATAPASS_KEY}":
            log.info("403: Bad authorization header for datapass call")
            return HttpResponseForbidden()
    except KeyError:
        log.info("403: No authorization header for datapass call")
        return HttpResponseForbidden()
    import json

    try:
        # if post data has json form
        content = json.loads(request.body)
    except json.decoder.JSONDecodeError:
        # if post data has querystring form
        content = request.POST

    form = DatapassForm(data=content)

    if form.is_valid():

        orga_type, _ = OrganisationType.objects.get_or_create(
            name=form.cleaned_data["organization_type"]
        )
        this_organisation = Organisation.objects.create(
            data_pass_id=form.cleaned_data["data_pass_id"],
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
