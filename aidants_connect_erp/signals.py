from django.dispatch import receiver

from aidants_connect_web.models import Aidant, HabilitationRequest
from aidants_connect_web.signals import aidant_activated

from .constants import SendingStatusChoices
from .models import CardSending


@receiver(aidant_activated)
def update_card_sendings(
    sender, aidant: Aidant, hrequest: HabilitationRequest, **kwargs
):
    sending, _ = CardSending.objects.get_or_create(
        organisation=aidant.organisation, status=SendingStatusChoices.PREPARING
    )

    if hrequest.connexion_mode == HabilitationRequest.CONNEXION_MODE_CARD:
        sending.estimated_quantity += 1
        sending.aidants.add(aidant)
        sending.save()
