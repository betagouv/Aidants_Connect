from __future__ import annotations

import logging
from enum import auto
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models, transaction
from django.db.models import IntegerChoices
from django.db.transaction import atomic
from django.utils.functional import cached_property

import requests

from aidants_connect_common.models import FormationAttendant

from ..constants import ReferentRequestStatuses
from .aidant import Aidant
from .organisation import Organisation

logger = logging.getLogger()


class HabilitationRequest(models.Model):
    ReferentRequestStatuses = ReferentRequestStatuses

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
        default=ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        choices=ReferentRequestStatuses.choices,
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

    formations = GenericRelation(
        FormationAttendant,
        related_name="aidant_requests",
        object_id_field="attendant_id",
        content_type_field="attendant_content_type",
    )

    @property
    def aidant_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def status_label(self):
        return ReferentRequestStatuses(self.status).label

    @property
    def status_cancellable_by_responsable(self):
        return (
            ReferentRequestStatuses(self.status)
            in ReferentRequestStatuses.cancellable_by_responsable()
        )

    @property
    def origin_label(self):
        return self.ORIGIN_LABELS[self.origin]

    def __str__(self):
        return f"{self.email}"

    def validate_and_create_aidant(self):
        if self.status not in (
            ReferentRequestStatuses.STATUS_PROCESSING,
            ReferentRequestStatuses.STATUS_NEW,
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
            ReferentRequestStatuses.STATUS_VALIDATED,
            ReferentRequestStatuses.STATUS_CANCELLED,
        ):
            return False

        with transaction.atomic():
            if Aidant.objects.filter(username__iexact=self.email).count() > 0:
                aidant: Aidant = Aidant.objects.get(username__iexact=self.email)
                aidant.organisations.add(self.organisation)
                aidant.is_active = True
                aidant.can_create_mandats = True
                aidant.save()
                self.status = ReferentRequestStatuses.STATUS_VALIDATED
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
            self.status = ReferentRequestStatuses.STATUS_VALIDATED
            self.save()

        from aidants_connect_web.signals import aidant_activated

        aidant_activated.send(self.__class__, aidant=aidant)

        return True

    def cancel_by_responsable(self):
        if not self.status_cancellable_by_responsable:
            return

        self.status = ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE
        self.save(update_fields={"status"})

    def generate_dict_for_sandbox(self):
        orga = self.organisation

        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "profession": self.profession,
            "email": self.email,
            "username": self.email,
            "organisation__data_pass_id": orga.data_pass_id,
            "organisation__name": orga.name,
            "organisation__siret": orga.siret,
            "organisation__address": orga.address,
            "organisation__city": orga.city,
            "organisation__zipcode": orga.zipcode,
            "datapass_id_managers": "",
            "token": settings.SANDBOX_API_TOKEN,
        }

    @classmethod
    def create_or_update_aidant_in_sandbox(cls, pk_hr: int):
        hr = cls.objects.get(pk=pk_hr)
        post_dict = hr.generate_dict_for_sandbox()
        return requests.post(settings.SANDBOX_API_URL, data=post_dict)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("email", "organisation"), name="unique_email_per_orga"
            ),
        )
        verbose_name = "aidant à former"
        verbose_name_plural = "aidants à former"


def _filepath_generator():
    return f"{uuid4()}.csv"


class ExportRequest(models.Model):
    class ExportRequestState(IntegerChoices):
        ONGOING = (auto(), "En cours")
        DONE = (auto(), "Fini")
        ERROR = (auto(), "Erreur")

    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    filename = models.CharField(max_length=40, default=_filepath_generator)
    state = models.IntegerField(
        "État", choices=ExportRequestState.choices, default=ExportRequestState.ONGOING
    )
    task_uuid = models.UUIDField(null=True, blank=False, default=None)

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

            super().save(*args, **kwargs)
            result = export_for_bizdevs.apply_async((self.pk,), compression="zlib")
            self.task_uuid = result.id
            super().save(update_fields=("task_uuid",))
        else:
            super().save(*args, **kwargs)


class CoReferentNonAidantRequest(models.Model):
    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)
    profession = models.CharField("Profession", max_length=150)
    email = models.EmailField("Email professionnel", max_length=150)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="co_referent_validation_requests",
    )
    status = models.CharField(
        "État",
        max_length=150,
        default=ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        choices=ReferentRequestStatuses.choices,
    )

    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def create_referent_non_aidant(self):
        if ReferentRequestStatuses(self.status) in [
            ReferentRequestStatuses.STATUS_REFUSED,
            ReferentRequestStatuses.STATUS_VALIDATED,
            ReferentRequestStatuses.STATUS_CANCELLED,
            ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE,
        ]:
            return None
        with atomic():
            instance = Aidant.objects.create(
                first_name=self.first_name,
                last_name=self.last_name,
                profession=self.profession,
                email=self.email,
                organisation=self.organisation,
                can_create_mandats=False,
                referent_non_aidant=True,
            )
            self.organisation.responsables.add(instance)
            self.status = ReferentRequestStatuses.STATUS_VALIDATED
            self.save(update_fields=("status",))
            return instance
