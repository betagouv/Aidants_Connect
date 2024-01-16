from __future__ import annotations

import logging
from enum import auto
from pathlib import Path
from uuid import uuid4

from django.db import models, transaction
from django.db.models import IntegerChoices
from django.utils.functional import cached_property

from ..constants import HabilitationRequestStatuses
from .aidant import Aidant
from .organisation import Organisation

logger = logging.getLogger()


class HabilitationRequest(models.Model):
    ORIGIN_DATAPASS = "datapass"
    ORIGIN_RESPONSABLE = "responsable"
    ORIGIN_OTHER = "autre"
    ORIGIN_HABILITATION = "habilitation"

    ORIGIN_LABELS = {
        ORIGIN_DATAPASS: "Datapass",
        ORIGIN_RESPONSABLE: "Référent Structure",
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
        default=HabilitationRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        choices=HabilitationRequestStatuses.choices,
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
            HabilitationRequestStatuses.STATUS_PROCESSING,
            HabilitationRequestStatuses.STATUS_NEW,
            HabilitationRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
            HabilitationRequestStatuses.STATUS_VALIDATED,
            HabilitationRequestStatuses.STATUS_CANCELLED,
        ):
            return False

        with transaction.atomic():
            if Aidant.objects.filter(username__iexact=self.email).count() > 0:
                aidant: Aidant = Aidant.objects.get(username__iexact=self.email)
                aidant.organisations.add(self.organisation)
                aidant.is_active = True
                aidant.can_create_mandats = True
                aidant.save()
                self.status = HabilitationRequestStatuses.STATUS_VALIDATED
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
            self.status = HabilitationRequestStatuses.STATUS_VALIDATED
            self.save()

        from aidants_connect_web.signals import aidant_activated

        aidant_activated.send(self.__class__, aidant=aidant)

        return True

    def cancel_by_responsable(self):
        if not self.status_cancellable_by_responsable:
            return

        self.status = HabilitationRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE
        self.save(update_fields={"status"})

    @property
    def status_label(self):
        return HabilitationRequestStatuses(self.status).label

    @property
    def status_cancellable_by_responsable(self):
        return (
            HabilitationRequestStatuses(self.status)
            in HabilitationRequestStatuses.cancellable_by_responsable()
        )

    @property
    def origin_label(self):
        return self.ORIGIN_LABELS[self.origin]


class IdGenerator(models.Model):
    code = models.CharField(max_length=100, unique=True)
    last_id = models.PositiveIntegerField()


def _filepath_generator():
    return f"{uuid4()}.csv"


class ExportRequest(models.Model):
    class ExportRequestState(IntegerChoices):
        ONGOING = auto()
        DONE = auto()
        ERROR = auto()

    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    filename = models.CharField(max_length=40, default=_filepath_generator)
    state = models.IntegerField(
        choices=ExportRequestState.choices, default=ExportRequestState.ONGOING
    )

    @property
    def is_ongoing(self):
        return self.state == self.ExportRequestState.ONGOING.value

    @property
    def is_done(self):
        return self.state == self.ExportRequestState.DONE.value

    @property
    def is_error(self):
        return self.state == self.ExportRequestState.ERROR.value

    @cached_property
    def file_path(self):
        import aidants_connect

        return Path(aidants_connect.__path__[0]).resolve().parent / self.filename

    def save(self, *args, **kwargs):
        if not self.pk:
            from ..tasks import export_for_bizdevs

            # Must save before export_for_bizdevs is called because if
            # export_for_bizdevs could save again before self.pk is set
            # which creates an infinite recursion and destroys the universe
            super().save(*args, **kwargs)
            export_for_bizdevs(self)
        else:
            super().save(*args, **kwargs)
