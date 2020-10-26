import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest

from aidants_connect_web.forms import DatapassForm
from aidants_connect_web.models import Organisation

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def receiver(request):

    if request.META["HTTP_AUTHORIZATION"] != settings.DATAPASS_KEY:
        log.info("403: Bad authorization header for datapass call")
        return HttpResponseForbidden()

    form = DatapassForm(data=request.POST)

    if form.is_valid():
        this_organisation = Organisation.objects.create(
            name=form.cleaned_data["organization_name"],
            siret=form.cleaned_data["organization_siret"],
            address=form.cleaned_data["organization_address"],
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
