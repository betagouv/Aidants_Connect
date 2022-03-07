from datetime import timedelta
from typing import Optional
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import SET_NULL, Q
from django.dispatch import Signal
from django.http import HttpRequest
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from phonenumber_field.modelfields import PhoneNumberField

from aidants_connect.common.constants import (
    MessageStakeholders,
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_web.models import OrganisationType

__all__ = [
    "PersonWithResponsibilities",
    "Issuer",
    "IssuerEmailConfirmation",
    "DataPrivacyOfficer",
    "Manager",
    "OrganisationRequest",
    "AidantRequest",
    "RequestMessage",
    "email_confirmation_sent",
]


def _new_uuid():
    return uuid4()


class Person(models.Model):
    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)
    email = models.EmailField("Email nominatif", max_length=150)
    profession = models.CharField("Profession", blank=False, max_length=150)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return str(self)

    class Meta:
        abstract = True


class PersonWithResponsibilities(Person):
    phone = PhoneNumberField("Téléphone", blank=True)

    class Meta:
        abstract = True


class Issuer(PersonWithResponsibilities):
    issuer_id = models.UUIDField(
        "Identifiant de demandeur", default=_new_uuid, unique=True
    )

    email_verified = models.BooleanField(verbose_name="Email vérifié", default=False)

    class Meta:
        verbose_name = "Demandeur"


class EmailConfirmationManager(models.Manager):
    def all_expired(self):
        return self.filter(self.expired_q())

    def all_valid(self):
        return self.exclude(self.expired_q())

    def expired_q(self):
        sent_threshold = now() - timedelta(days=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS)
        return Q(sent__lt=sent_threshold)

    def delete_expired_confirmations(self):
        self.all_expired().delete()


email_confirmation_sent = Signal()


def _get_default_email_key():
    return get_random_string(64).lower()


class IssuerEmailConfirmation(models.Model):
    issuer = models.ForeignKey(
        Issuer, on_delete=models.CASCADE, related_name="email_confirmations"
    )
    created = models.DateTimeField(verbose_name="Créé le", default=now)
    sent = models.DateTimeField(verbose_name="Envoyée", null=True)
    key = models.CharField(
        verbose_name="Clé", max_length=64, unique=True, default=_get_default_email_key
    )

    objects = EmailConfirmationManager()

    @property
    def key_expired(self) -> bool:
        expiration_date = self.sent + timedelta(
            days=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS
        )
        return expiration_date <= now()

    class Meta:
        verbose_name = "Confirmation d'email"
        verbose_name_plural = "Confirmations d'email"

    def __str__(self):
        return "Confirmation pour %s" % self.issuer.email

    @classmethod
    def for_issuer(cls, issuer) -> "IssuerEmailConfirmation":
        return cls._default_manager.create(issuer=issuer)

    def confirm(self) -> Optional[str]:
        if self.issuer.email_verified:
            return self.issuer.email

        if self.key_expired:
            return None

        self.issuer.email_verified = True
        self.issuer.save()

        return self.issuer.email

    def send(self, request: HttpRequest):
        self.sent = now()
        self.save()
        email_confirmation_sent.send(self.__class__, request=request, confirmation=self)


class DataPrivacyOfficer(PersonWithResponsibilities):
    pass


class Manager(PersonWithResponsibilities):
    address = models.TextField("Adresse")
    zipcode = models.CharField("Code Postal", max_length=10)
    city = models.CharField("Ville", max_length=255)

    is_aidant = models.BooleanField("C'est aussi un aidant", default=False)


class OrganisationRequest(models.Model):
    issuer = models.ForeignKey(
        Issuer,
        on_delete=models.CASCADE,
        related_name="organisation_requests",
        verbose_name="Demandeur",
    )

    manager = models.OneToOneField(
        Manager,
        on_delete=models.CASCADE,
        related_name="organisation",
        verbose_name="Responsable",
        default=None,
        null=True,
    )

    data_privacy_officer = models.OneToOneField(
        DataPrivacyOfficer,
        on_delete=models.CASCADE,
        related_name="organisation",
        verbose_name="Délégué à la protection des données",
        default=None,
        null=True,
    )

    draft_id = models.UUIDField(
        "Identifiant de brouillon",
        null=True,
        default=_new_uuid,
        unique=True,
    )

    status = models.CharField(
        "État",
        max_length=150,
        default=RequestStatusConstants.NEW.name,
        choices=RequestStatusConstants.choices(),
    )

    type = models.ForeignKey(OrganisationType, null=True, on_delete=SET_NULL)

    type_other = models.CharField(
        "Type de structure si autre",
        blank=True,
        default="",
        max_length=200,
    )

    # Organisation
    name = models.TextField("Nom de la structure")
    siret = models.BigIntegerField("N° SIRET")
    address = models.TextField("Adresse")
    zipcode = models.CharField("Code Postal", max_length=10)
    city = models.CharField("Ville", max_length=255, blank=True)

    partner_administration = models.CharField(
        "Administration partenaire",
        blank=True,
        default="",
        max_length=200,
    )

    public_service_delegation_attestation = models.FileField(
        "Attestation de délégation de service public",
        blank=True,
        default="",
    )

    france_services_label = models.BooleanField(
        "Labellisation France Services", default=False
    )

    web_site = models.URLField("Site web", blank=True, default="")

    mission_description = models.TextField("Description des missions de la structure")

    avg_nb_demarches = models.IntegerField(
        "Nombre moyen de démarches ou de dossiers traités par semaine"
    )

    # Checkboxes
    cgu = models.BooleanField("J'accepte les CGU", default=False)
    dpo = models.BooleanField("Le DPO est informé", default=False)
    professionals_only = models.BooleanField(
        "La structure ne contient que des aidants professionnels", default=False
    )
    without_elected = models.BooleanField(
        "Aucun élu n'est impliqué dans la structure", default=False
    )

    @property
    def is_draft(self):
        return self.draft_id is not None

    @property
    def status_label(self):
        return RequestStatusConstants[self.status].value

    def confirm_request(self):
        self.draft_id = None
        self.save()

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        ~Q(type_id=RequestOriginConstants.OTHER.value)
                        & Q(type_other__isnull_or_blank=True)
                    )
                    | (
                        Q(type_id=RequestOriginConstants.OTHER.value)
                        & Q(type_other__isnull_or_blank=False)
                    )
                ),
                name="type_other_correctly_set",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(cgu=True)),
                name="cgu_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(dpo=True)),
                name="dpo_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(professionals_only=True)),
                name="professionals_only_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(without_elected=True)),
                name="without_elected_checked",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(manager__isnull=False)),
                name="manager_set",
            ),
            models.CheckConstraint(
                check=Q(draft_id__isnull=False)
                | (Q(draft_id__isnull=True) & Q(data_privacy_officer__isnull=False)),
                name="data_privacy_officer_set",
            ),
        ]
        verbose_name = "Demande d’habilitation"
        verbose_name_plural = "Demandes d’habilitation"


class AidantRequest(Person):
    organisation = models.ForeignKey(
        OrganisationRequest,
        on_delete=models.CASCADE,
        related_name="aidant_requests",
    )

    @property
    def is_draft(self):
        return self.organisation.is_draft

    @property
    def draft_id(self):
        return self.organisation.draft_id

    class Meta:
        verbose_name = "aidant à habiliter"
        verbose_name_plural = "aidants à habiliter"


class RequestMessage(models.Model):
    organisation = models.ForeignKey(
        OrganisationRequest,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.CharField(
        "Expéditeur", max_length=20, choices=MessageStakeholders.choices()
    )
    content = models.TextField("Message")

    def __str__(self):
        return f"Message {self.id}"

    class Meta:
        verbose_name = "message"
