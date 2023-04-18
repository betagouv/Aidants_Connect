from datetime import timedelta
from typing import Optional
from uuid import uuid4

from django.conf import settings
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models import SET_NULL, Q
from django.db.utils import IntegrityError
from django.dispatch import Signal
from django.http import HttpRequest
from django.template import loader
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from phonenumber_field.modelfields import PhoneNumberField

from aidants_connect_common.utils.constants import (
    MessageStakeholders,
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_web.models import (
    Aidant,
    HabilitationRequest,
    Organisation,
    OrganisationType,
)
from aidants_connect_web.utilities import generate_new_datapass_id

__all__ = [
    "PersonWithResponsibilities",
    "Issuer",
    "IssuerEmailConfirmation",
    "Manager",
    "OrganisationRequest",
    "AidantRequest",
    "RequestMessage",
    "email_confirmation_sent",
]


def _new_uuid():
    return uuid4()


class PersonEmailField(models.EmailField):
    def __init__(self, **kwargs):
        kwargs["max_length"] = 150
        kwargs["verbose_name"] = "Email nominatif"
        super().__init__(**kwargs)


class Person(models.Model):
    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)
    email = PersonEmailField()
    profession = models.CharField("Profession", blank=False, max_length=150)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.email:
            self.email = self.email.lower()
        if update_fields is not None:
            update_fields = {"email"}.union(update_fields)
        super().save(force_insert, force_update, using, update_fields)

    def get_full_name(self):
        return str(self)

    class Meta:
        abstract = True


class PersonWithResponsibilities(Person):
    phone = PhoneNumberField("Téléphone", blank=True)

    class Meta:
        abstract = True


class Issuer(PersonWithResponsibilities):
    email = PersonEmailField(unique=True)
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


class Manager(PersonWithResponsibilities):
    address = models.TextField("Adresse")
    zipcode = models.CharField("Code Postal", max_length=10)
    city = models.CharField("Ville", max_length=255)

    city_insee_code = models.CharField(
        "Code INSEE de la ville", max_length=5, null=True, blank=True
    )

    department_insee_code = models.CharField(
        "Code INSEE du département", max_length=5, null=True, blank=True
    )

    is_aidant = models.BooleanField("C'est aussi un aidant", default=False)

    class Meta:
        verbose_name = "Responsable structure"
        verbose_name_plural = "Responsables structure"


class OrganisationRequest(models.Model):
    created_at = models.DateTimeField("Date création", auto_now_add=True)

    updated_at = models.DateTimeField("Date modification", auto_now=True)

    organisation = models.ForeignKey(
        Organisation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

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

    uuid = models.UUIDField(
        "Identifiant de brouillon",
        default=_new_uuid,
        unique=True,
    )

    data_pass_id = models.IntegerField(
        "Numéro Datapass",
        null=True,
        default=None,
        unique=True,
    )

    status = models.CharField(
        "État",
        max_length=150,
        default=RequestStatusConstants.NEW.name,
        choices=RequestStatusConstants.choices,
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

    city_insee_code = models.CharField(
        "Code INSEE de la ville", max_length=5, null=True, blank=True
    )

    department_insee_code = models.CharField(
        "Code INSEE du département", max_length=5, null=True, blank=True
    )

    is_private_org = models.BooleanField("Structure privée", default=False)
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
    france_services_number = models.CharField(
        "Numéro d’immatriculation France Services",
        blank=True,
        default="",
        max_length=200,
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
        return RequestStatusConstants[self.status] == RequestStatusConstants.NEW

    @property
    def status_label(self):
        return RequestStatusConstants[self.status].label

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            "habilitation_organisation_view",
            kwargs={"issuer_id": self.issuer.issuer_id, "uuid": self.uuid},
        )

    def notify_issuer_request_submitted(self):
        context = {
            "url": f"https://{settings.HOST}{self.get_absolute_url()}",
            "organisation": self,
        }
        text_message = loader.render_to_string(
            "email/organisation_request_creation.txt", context
        )
        html_message = loader.render_to_string(
            "email/organisation_request_creation.html", context
        )

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=[self.issuer.email],
            subject=settings.EMAIL_ORGANISATION_REQUEST_SUBMISSION_SUBJECT,
            message=text_message,
            html_message=html_message,
        )

    def notify_issuer_request_modified(self):
        context = {
            "url": f"https://{settings.HOST}{self.get_absolute_url()}",
            "organisation": self,
        }
        text_message = loader.render_to_string(
            "email/organisation_request_modifications_done.txt", context
        )
        html_message = loader.render_to_string(
            "email/organisation_request_modifications_done.html", context
        )

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=[self.issuer.email],
            subject=settings.EMAIL_ORGANISATION_REQUEST_MODIFICATION_SUBJECT,
            message=text_message,
            html_message=html_message,
        )

    def prepare_request_for_ac_validation(self, form_data: dict):
        self.cgu = form_data["cgu"]
        self.dpo = form_data["dpo"]
        self.professionals_only = form_data["professionals_only"]
        self.without_elected = form_data["without_elected"]
        if self.status == RequestStatusConstants.NEW.name:
            self.status = RequestStatusConstants.AC_VALIDATION_PROCESSING.name
            self.data_pass_id = int(f"{self.zipcode[:3]}{generate_new_datapass_id()}")
            self.save()
            self.notify_issuer_request_submitted()
        if self.status == RequestStatusConstants.CHANGES_REQUIRED.name:
            self.status = RequestStatusConstants.AC_VALIDATION_PROCESSING.name
            self.save()
            self.notify_issuer_request_modified()

    @transaction.atomic
    def go_in_waiting_again(self):
        self.status = RequestStatusConstants.AC_VALIDATION_PROCESSING.name
        self.save()

    @transaction.atomic
    def accept_request_and_create_organisation(self):
        if self.status != RequestStatusConstants.AC_VALIDATION_PROCESSING.name:
            return False

        try:
            organisation_type, _ = OrganisationType.objects.get_or_create(
                name=(self.type_other if self.type_other else self.type)
            )
            organisation = Organisation.objects.create(
                name=self.name,
                type=organisation_type,
                siret=self.siret,
                address=self.address,
                zipcode=self.zipcode,
                city=self.city,
                city_insee_code=self.city_insee_code,
                department_insee_code=self.department_insee_code,
                data_pass_id=self.data_pass_id,
            )
        except IntegrityError:
            raise Organisation.AlreadyExists(
                "Il existe déjà une organisation portant le n° datapass "
                f"{self.data_pass_id}."
            )

        self.organisation = organisation
        self.status = RequestStatusConstants.VALIDATED.name
        self.save()

        responsable_query = Aidant.objects.filter(username__iexact=self.manager.email)

        if not responsable_query.exists():
            responsable = Aidant.objects.create(
                first_name=self.manager.first_name,
                last_name=self.manager.last_name,
                email=self.manager.email,
                username=self.manager.email,
                phone=self.manager.phone,
                profession=self.manager.profession,
                organisation=organisation,
                can_create_mandats=False,
            )

            responsable.responsable_de.add(organisation)
            responsable.save()
        else:
            responsable = responsable_query[0]
            responsable.responsable_de.add(organisation)
            if responsable.has_a_totp_device:
                self.status = RequestStatusConstants.CLOSED.name
                self.save()
            responsable.save()

        self.create_aidants(organisation)

        if self.manager.is_aidant:
            HabilitationRequest.objects.get_or_create(
                email=self.manager.email,
                organisation=organisation,
                defaults=dict(
                    origin=HabilitationRequest.ORIGIN_HABILITATION,
                    first_name=self.manager.first_name,
                    last_name=self.manager.last_name,
                    profession=self.manager.profession,
                ),
            )

        return True

    @transaction.atomic
    def create_aidants(self, organisation: Organisation):
        for aidant in self.aidant_requests.all():
            HabilitationRequest.objects.get_or_create(
                email=aidant.email,
                organisation=organisation,
                defaults=dict(
                    origin=HabilitationRequest.ORIGIN_HABILITATION,
                    first_name=aidant.first_name,
                    last_name=aidant.last_name,
                    profession=aidant.profession,
                ),
            )

    def refuse_request(self):
        if self.status != RequestStatusConstants.AC_VALIDATION_PROCESSING.name:
            return False
        self.status = RequestStatusConstants.REFUSED.name
        self.save()
        return True

    def require_changes_request(self):
        if self.status != RequestStatusConstants.AC_VALIDATION_PROCESSING.name:
            return False
        self.status = RequestStatusConstants.CHANGES_REQUIRED.name
        self.save()
        return True

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
                check=(
                    (
                        Q(is_private_org=True)
                        & Q(partner_administration__isnull_or_blank=False)
                    )
                    | (
                        Q(is_private_org=False)
                        & Q(partner_administration__isnull_or_blank=True)
                    )
                ),
                name="partner_administration_if_org_is_private",
            ),
            models.CheckConstraint(
                check=(
                    (
                        Q(france_services_label=True)
                        & Q(france_services_number__isnull_or_blank=False)
                    )
                    | (
                        Q(france_services_label=False)
                        & Q(france_services_number__isnull_or_blank=True)
                    )
                ),
                name="immatriculation_number_if_france_services_label",
            ),
            models.CheckConstraint(
                check=Q(status=RequestStatusConstants.NEW.name)
                | (~Q(status=RequestStatusConstants.NEW.name) & Q(cgu=True)),
                name="cgu_checked",
            ),
            models.CheckConstraint(
                check=Q(status=RequestStatusConstants.NEW.name)
                | (~Q(status=RequestStatusConstants.NEW.name) & Q(dpo=True)),
                name="dpo_checked",
            ),
            models.CheckConstraint(
                check=Q(status=RequestStatusConstants.NEW.name)
                | (
                    ~Q(status=RequestStatusConstants.NEW.name)
                    & Q(professionals_only=True)
                ),
                name="professionals_only_checked",
            ),
            models.CheckConstraint(
                check=Q(status=RequestStatusConstants.NEW.name)
                | (
                    ~Q(status=RequestStatusConstants.NEW.name) & Q(without_elected=True)
                ),
                name="without_elected_checked",
            ),
            models.CheckConstraint(
                check=Q(status=RequestStatusConstants.NEW.name)
                | (
                    ~Q(status=RequestStatusConstants.NEW.name)
                    & Q(manager__isnull=False)
                ),
                name="manager_set",
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
    def uuid(self):
        return self.organisation.uuid

    class Meta:
        verbose_name = "aidant à habiliter"
        verbose_name_plural = "aidants à habiliter"
        unique_together = (("email", "organisation"),)


class RequestMessage(models.Model):
    organisation = models.ForeignKey(
        OrganisationRequest,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.CharField(
        "Expéditeur", max_length=20, choices=MessageStakeholders.choices
    )
    content = models.TextField("Message")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message {self.id}"

    class Meta:
        verbose_name = "message"
        ordering = ("created_at",)

    def send_message_email(self):
        context = {
            "url": f"https://{settings.HOST}{self.organisation.get_absolute_url()}",
            "organisation": self.organisation,
            "message": self,
        }
        text_message = loader.render_to_string(
            "email/new_message_received.txt", context
        )
        html_message = loader.render_to_string(
            "email/new_message_received.html", context
        )

        send_mail(
            from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
            recipient_list=[self.organisation.issuer.email],
            subject=settings.EMAIL_NEW_MESSAGE_RECEIVED_SUBJECT,
            message=text_message,
            html_message=html_message,
        )

    def save(self, *args, **kwargs):
        if not self.pk and self.sender == "AC":
            self.send_message_email()
        return super(RequestMessage, self).save(*args, **kwargs)


def _default_expiraton_date():
    return now() + timedelta(days=1)


class AddressAPIResultQuerySet(models.QuerySet):
    def expired(self):
        return self.filter(expiraton_date__lt=now())
