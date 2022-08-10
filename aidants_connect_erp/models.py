from django.db import models

from aidants_connect_web.models import Organisation

from .constants import SendingStatusChoices


class CardSending(models.Model):

    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    tracking = models.CharField(
        "Information transporteur", null=True, blank=True, max_length=200
    )
    command_number = models.CharField(
        "Bon commande client", null=True, blank=True, max_length=200
    )
    sending_date = models.DateField("Date d'envoi", null=True, blank=True)
    receipt_date = models.DateField("Date de livraison prévue", null=True, blank=True)
    quantity = models.PositiveIntegerField("Quantité", default=1)
    status = models.CharField(
        "statut d'envoi", choices=SendingStatusChoices.choices, max_length=200
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        verbose_name="Organisation",
        related_name="card_sendings",
    )

    def __str__(self):
        sending_date = (
            self.sending_date.strftime("%d/%m/%Y") if self.sending_date else "NC"
        )
        return f"{self.organisation} - {self.status} - {self.quantity} - {sending_date}"
