from __future__ import annotations

import logging
from enum import auto
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import IntegerChoices
from django.db.transaction import atomic
from django.utils.functional import cached_property

import pgtrigger

from ..constants import ReferentRequestStatuses
from .aidant import Aidant
from .organisation import Organisation

logger = logging.getLogger()


class FormationType(models.Model):
    label = models.CharField("Type", blank=False)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = "Type de formation aidant"
        verbose_name_plural = "Types de formation aidant"
        constraints = [
            models.CheckConstraint(
                check=models.Q(label__isnull_or_blank=False), name="not_blank_label"
            )
        ]


class Formation(models.Model):
    class Status(models.IntegerChoices):
        PRESENTIAL = (auto(), "En présentiel")
        REMOTE = (auto(), "À distance")

    start_datetime = models.DateTimeField("Date et heure de début de la formation")
    end_datetime = models.DateTimeField("Date et heure de fin de la formation")
    duration = models.IntegerField("Durée en heures")
    max_attendants = models.IntegerField("Nombre maximum d'inscrits possibles")
    status = models.IntegerField("En présentiel/à distance", choices=Status.choices)
    place = models.CharField("Lieu", max_length=500)
    type = models.ForeignKey(FormationType, on_delete=models.PROTECT)

    @property
    def number_of_attendants(self):
        return self.attendants.count()

    def __str__(self):
        return self.type.label

    def register_attendant(self, obj):
        return FormationAttendant.objects.create(formation=self, attendant=obj)

    def unregister_attendant(self, obj):
        FormationAttendant.objects.filter(formation=self, attendant=obj).delete()

    class Meta:
        verbose_name = "Formation aidant"
        verbose_name_plural = "Formations aidant"
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_datetime__lt=models.F("end_datetime")),
                name="must_starts_before_it_ends",
            ),
            models.CheckConstraint(
                check=models.Q(duration__gt=0), name="must_be_a_non_0_duration"
            ),
            models.CheckConstraint(
                check=models.Q(max_attendants__gt=0), name="cant_have_0_max_attendants"
            ),
        ]


class FormationAttendant(models.Model):
    attendant_content_type = models.ForeignKey(
        ContentType,
        editable=False,
        related_name="%(app_label)s_%(class)s_formations_attendants",
        on_delete=models.CASCADE,
    )
    attendant_id = models.PositiveIntegerField()
    attendant = GenericForeignKey("attendant_content_type", "attendant_id")
    formation = models.ForeignKey(
        Formation, on_delete=models.PROTECT, related_name="attendants"
    )

    class Meta:
        # One attendant a type can only be registered only once to a specific formation
        unique_together = ("attendant_content_type", "attendant_id", "formation")
        triggers = [
            pgtrigger.Trigger(
                name="check_attendants_count",
                when=pgtrigger.Before,
                operation=(pgtrigger.Insert | pgtrigger.Update),
                declare=[
                    ("attendants_count", "INTEGER"),
                    ("max_attendants_count", "INTEGER"),
                ],
                func=pgtrigger.Func(
                    dedent(
                        f"""
                        -- prevent concurrent inserts from multiple transactions
                        LOCK TABLE {{meta.db_table}} IN EXCLUSIVE MODE;

                        SELECT INTO attendants_count COUNT(*) 
                        FROM {{meta.db_table}} 
                        WHERE {{columns.formation}} = NEW.{{columns.formation}};

                        SELECT {Formation._meta.get_field('max_attendants').name} INTO max_attendants_count
                        FROM {Formation._meta.db_table} 
                        WHERE {Formation._meta.pk.name} = NEW.{{columns.formation}};

                        IF attendants_count >= max_attendants_count THEN
                            RAISE EXCEPTION 'Formation is already full.' USING ERRCODE = 'check_violation';
                        END IF;

                        RETURN NEW;
                        """  # noqa: E501, W291
                    ).strip()
                ),
            )
        ]


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

    formation = GenericRelation(Formation, related_name="habilitation_requests")

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

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("email", "organisation"), name="unique_email_per_orga"
            ),
        )
        verbose_name = "aidant à former"
        verbose_name_plural = "aidants à former"


class IdGenerator(models.Model):
    code = models.CharField(max_length=100, unique=True)
    last_id = models.PositiveIntegerField()


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
