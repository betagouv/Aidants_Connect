from django.utils import timezone

from factory import SubFactory
from factory.django import DjangoModelFactory

from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory

from ..constants import SendingStatusChoices
from ..models import CardSending


class CardSendingFactory(DjangoModelFactory):
    sending_date = timezone.now()
    organisation = SubFactory(OrganisationFactory)
    referent = SubFactory(AidantFactory)
    bizdev = SubFactory(AidantFactory)
    quantity = 1
    status = SendingStatusChoices.SENDING

    class Meta:
        model = CardSending
