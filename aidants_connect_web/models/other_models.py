from __future__ import annotations

import logging

from django.db import models, transaction

from .aidant import Aidant
from .organisation import Organisation

logger = logging.getLogger()


class HabilitationRequest(models.Model):
    STATUS_WAITING_LIST_HABILITATION = "habilitation_waitling_list"
    STATUS_NEW = "new"
    STATUS_PROCESSING = "processing"
    STATUS_VALIDATED = "validated"
    STATUS_REFUSED = "refused"
    STATUS_CANCELLED = "cancelled"

    ORIGIN_DATAPASS = "datapass"
    ORIGIN_RESPONSABLE = "responsable"
    ORIGIN_OTHER = "autre"
    ORIGIN_HABILITATION = "habilitation"

    STATUS_LABELS = {
        STATUS_WAITING_LIST_HABILITATION: "Liste d'attente",
        STATUS_NEW: "Nouvelle",
        STATUS_PROCESSING: "En cours",
        STATUS_VALIDATED: "Validée",
        STATUS_REFUSED: "Refusée",
        STATUS_CANCELLED: "Annulée",
    }

    ORIGIN_LABELS = {
        ORIGIN_DATAPASS: "Datapass",
        ORIGIN_RESPONSABLE: "Responsable Structure",
        ORIGIN_OTHER: "Autre",
        ORIGIN_HABILITATION: "Formulaire Habilitation",
    }

    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)
    email = models.EmailField(
        max_length=150,
    )
    organisation = models.ForeignKey(
        Organisation,
        null=True,
        on_delete=models.CASCADE,
        related_name="habilitation_requests",
    )
    profession = models.CharField(blank=False, max_length=150)
    status = models.CharField(
        "État",
        blank=False,
        max_length=150,
        default=STATUS_WAITING_LIST_HABILITATION,
        choices=((status, label) for status, label in STATUS_LABELS.items()),
    )
    origin = models.CharField(
        "Origine",
        blank=False,
        max_length=150,
        choices=((origin, label) for origin, label in ORIGIN_LABELS.items()),
        default=ORIGIN_OTHER,
    )

    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    formation_done = models.BooleanField("Formation faite", default=False)
    date_formation = models.DateTimeField("Date de formation", null=True, blank=True)
    test_pix_passed = models.BooleanField("Test PIX", default=False)
    date_test_pix = models.DateTimeField("Date test PIX", null=True, blank=True)

    @property
    def aidant_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("email", "organisation"), name="unique_email_per_orga"
            ),
        )
        verbose_name = "aidant à former"
        verbose_name_plural = "aidants à former"

    def __str__(self):
        return f"{self.email}"

    def validate_and_create_aidant(self):
        if self.status not in (
            self.STATUS_PROCESSING,
            self.STATUS_NEW,
            self.STATUS_WAITING_LIST_HABILITATION,
            self.STATUS_VALIDATED,
            self.STATUS_CANCELLED,
        ):
            return False

        with transaction.atomic():
            if Aidant.objects.filter(username__iexact=self.email).count() > 0:
                aidant: Aidant = Aidant.objects.get(username__iexact=self.email)
                aidant.organisations.add(self.organisation)
                aidant.is_active = True
                aidant.can_create_mandats = True
                aidant.save()
                self.status = self.STATUS_VALIDATED
                self.save()
                return True

            aidant = Aidant.objects.create(
                last_name=self.last_name,
                first_name=self.first_name,
                profession=self.profession,
                organisation=self.organisation,
                email=self.email,
                username=self.email,
            )
            self.status = self.STATUS_VALIDATED
            self.save()

        # Prevent circular import
        from aidants_connect_web.tasks import email_welcome_aidant

        email_welcome_aidant(aidant.email, logger=logger)

        return True

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status]

    @property
    def origin_label(self):
        return self.ORIGIN_LABELS[self.origin]


class IdGenerator(models.Model):
    code = models.CharField(max_length=100, unique=True)
    last_id = models.PositiveIntegerField()
