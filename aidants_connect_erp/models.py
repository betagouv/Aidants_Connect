from django.conf import settings
from django.db import models

from .constants import SendingStatusChoices


def get_bizdev_users():
    from aidants_connect_web.models import Aidant

    stafforg = settings.STAFF_ORGANISATION_NAME
    bizdevs = Aidant.objects.filter(
        organisation__name=stafforg, is_active=True, is_staff=True
    )
    return bizdevs


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
    quantity = models.PositiveIntegerField("Nombre de cartes", default=1)
    kit_quantity = models.PositiveIntegerField("Nombres de kits", default=0)
    status = models.CharField(
        "statut d'envoi", choices=SendingStatusChoices.choices, max_length=200
    )

    organisation = models.ForeignKey(
        "aidants_connect_web.Organisation",
        on_delete=models.CASCADE,
        verbose_name="Organisation",
        related_name="card_sendings",
    )
    raison_envoi = models.TextField("Raison de l'envoi", null=True, blank=True)

    referent = models.ForeignKey(
        "aidants_connect_web.Aidant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="referent_for_sendings",
    )

    responsable = models.ForeignKey(
        "aidants_connect_web.Aidant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="card_sendings",
    )
    code_responsable = models.CharField(
        "Code premier envoi", null=True, blank=True, max_length=25
    )

    def __str__(self):
        sending_date = (
            self.sending_date.strftime("%d/%m/%Y") if self.sending_date else "NC"
        )
        return f"{self.organisation} - {self.status} - {self.quantity} - {sending_date}"

    def get_organisation_data_pass_id(self):
        return self.organisation.data_pass_id

    get_organisation_data_pass_id.short_description = "Datapass ID"

    def get_sending_year(self):
        if self.sending_date:
            return self.sending_date.year
        return "NC"

    get_sending_year.short_description = "Année d'envoi"

    def get_responsable_email(self):
        if self.responsable:
            return self.responsable.email
        return "NC"

    get_responsable_email.short_description = "Email Responsable"

    def get_responsable_phone(self):
        if self.responsable:
            return self.responsable.phone
        return "NC"

    get_responsable_phone.short_description = "Téléphone Responsable"

    def get_organisation_address(self):
        return self.organisation.address

    get_organisation_address.short_description = "Adresse"

    def get_organisation_zipcode(self):
        return self.organisation.zipcode

    get_organisation_zipcode.short_description = "Code Postal"

    def get_organisation_city(self):
        return self.organisation.city

    get_organisation_city.short_description = "Ville"

    def get_organisation_region_name(self):
        if self.organisation.region:
            return self.organisation.region.name
        return "NC"

    get_organisation_region_name.short_description = "Région"
