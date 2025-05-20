from django.conf import settings
from django.db import models
from django.db.models import Sum

from .constants import SendingStatusChoices


def get_bizdev_users():
    from aidants_connect_web.models import Aidant

    stafforg = settings.STAFF_ORGANISATION_NAME
    bizdevs = Aidant.objects.filter(organisation__name=stafforg, is_staff=True)
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
    estimated_quantity = models.PositiveIntegerField(
        "Nombre de cartes estimé", default=0
    )

    status = models.CharField(
        "statut d'envoi", choices=SendingStatusChoices.choices, max_length=200
    )

    organisation = models.ForeignKey(
        "aidants_connect_web.Organisation",
        on_delete=models.CASCADE,
        verbose_name="Organisation",
        related_name="card_sendings",
    )

    aidants = models.ManyToManyField(
        "aidants_connect_web.Aidant",
        verbose_name="Aidants concernés par l'envoi",
    )

    raison_envoi = models.TextField("Raison de l'envoi", null=True, blank=True)

    referent = models.ForeignKey(
        "aidants_connect_web.Aidant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="referent_for_sendings",
    )

    phone_referent = models.CharField(
        "Telephone referent (GRIST)", null=True, blank=True, max_length=125
    )
    name_referent = models.CharField(
        "Nom referent (GRIST)", null=True, blank=True, max_length=125
    )
    email_referent = models.CharField(
        "Email referent (GRIST)", null=True, blank=True, max_length=125
    )
    code_referent = models.CharField(
        "Code premier envoi", null=True, blank=True, max_length=25
    )

    bizdev = models.ForeignKey(
        "aidants_connect_web.Aidant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="card_sendings",
    )

    id_grist = models.CharField(
        "Id Grist", editable=False, max_length=50, blank=True, default="", null=True
    )

    @classmethod
    def get_cards_stock_for_one_organisation(cls, organisation):
        dict_stock = cls.objects.filter(
            organisation=organisation,
            status__in=[SendingStatusChoices.SENDING, SendingStatusChoices.RECEIVED],
        ).aggregate(stock=Sum("quantity"))
        return dict_stock["stock"]

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

    def get_referent_email(self):
        if self.referent:
            return self.referent.email
        return self.email_referent

    get_referent_email.short_description = "Email référent"

    def get_referent_phone(self):
        if self.referent:
            return self.referent.phone
        return self.phone_referent

    get_referent_phone.short_description = "Téléphone référent"

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
