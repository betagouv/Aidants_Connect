from __future__ import annotations

from datetime import timedelta
from enum import auto
from typing import TYPE_CHECKING, Any, Self

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CASCADE, Count
from django.template.defaultfilters import date
from django.utils.safestring import mark_safe
from django.utils.timezone import now

import pgtrigger

from aidants_connect_common.constants import FormationAttendantState
from aidants_connect_common.utils import PGTriggerExtendedFunc, render_markdown
from aidants_connect_pico_cms.fields import MarkdownField

if TYPE_CHECKING:
    from aidants_connect_web.models import HabilitationRequest


class Region(models.Model):
    insee_code = models.CharField(
        "Code INSEE", max_length=2, unique=True, primary_key=True
    )
    name = models.CharField("Nom de région", max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Région"


class Department(models.Model):
    insee_code = models.CharField(
        "Code INSEE", max_length=3, unique=True, primary_key=True
    )
    zipcode = models.CharField("Code Postal", max_length=5)
    name = models.CharField("Nom du département", max_length=50, unique=True)
    region = models.ForeignKey(Region, on_delete=CASCADE, related_name="department")

    def __str__(self):
        return self.name

    @staticmethod
    def extract_dept_zipcode(code: Any):
        code = str(code).upper()
        if code.startswith("2A") or code.startswith("2B"):
            return "20"
        elif code.startswith("97"):
            return code[:3]

        return code[:2]

    class Meta:
        verbose_name = "Département"


class Commune(models.Model):
    insee_code = models.CharField(
        "Code INSEE", max_length=5, unique=True, primary_key=True
    )
    name = models.TextField("Nom de la commune")
    zrr = models.BooleanField("Commune classé en zone rurale restreinte", default=False)
    department = models.ForeignKey(
        Department, on_delete=CASCADE, related_name="commune"
    )

    def __str__(self):
        return f"{self.name} ({self.insee_code})"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        """
        WARNING: Do not override, this logic won't be called when importing from
        INSEE's CSV.
        """
        super().save(force_insert, force_update, using, update_fields)


class MarkdownContentMixin(models.Model):
    body = MarkdownField("Contenu")

    def to_html(self):
        return mark_safe(render_markdown(self.body))

    class Meta:
        abstract = True


class FormationType(models.Model):
    label = models.CharField("Type", blank=False)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = "Formation : types"
        verbose_name_plural = "Formation : types"
        constraints = [
            models.CheckConstraint(
                check=models.Q(label__isnull_or_blank=False), name="not_blank_label"
            )
        ]


class FormationOrganizationQuerySet(models.QuerySet):
    def warnable_about_new_attendants(self):
        return self.annotate(nb=Count("formations__attendants")).filter(
            contacts__len__gt=0,
            formations__attendants__organization_warned_at__isnull=True,
            nb__gt=0,
        )


class FormationOrganization(models.Model):
    name = models.CharField("Nom")
    contacts = ArrayField(
        models.EmailField(),
        default=list,
        verbose_name="Contacts publics",
        null=True,
        blank=True,
    )
    private_contacts = ArrayField(
        models.EmailField(),
        default=list,
        verbose_name="Contacts privés",
        null=True,
        blank=True,
    )
    type = models.ForeignKey(
        FormationType, default=None, null=True, blank=True, on_delete=models.SET_NULL
    )
    region = models.ForeignKey(
        Region, default=None, null=True, blank=True, on_delete=models.SET_NULL
    )

    objects = FormationOrganizationQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Formation : organisation"
        verbose_name_plural = "Formation : organisation"
        constraints = [
            models.CheckConstraint(
                check=models.Q(name__isnull_or_blank=False), name="not_blank_name"
            )
        ]


class FormationQuerySet(models.QuerySet):
    def for_attendant_q(self, attendant: HabilitationRequest):
        return models.Q(attendants__attendant_id=attendant.pk)

    def get_q_available_now(self):
        att_count = settings.SHORT_TIMEDELTA_ATTENDANTS_COUNT_FOR_INSCRIPTION
        short_td = timedelta(days=settings.SHORT_TIMEDELTA_IN_DAYS_FOR_INSCRIPTION)
        long_td = timedelta(days=settings.TIMEDELTA_IN_DAYS_FOR_INSCRIPTION)

        q = models.Q(
            attendants_count__lt=models.F("max_attendants"),
            state=Formation.State.ACTIVE,
            intra=False,
        ) & (
            models.Q(
                attendants_count__gt=att_count, start_datetime__gte=now() + short_td
            )
            | models.Q(
                attendants_count__lte=att_count,
                start_datetime__gte=now() + long_td,
            )
        )
        return q

    def available_now(self):
        q = self.get_q_available_now()
        return (
            self.annotate(attendants_count=Count("attendants"))
            .filter(q)
            .order_by("start_datetime")
            .distinct()
        )

    def available_for_attendant(self, attendant: HabilitationRequest) -> Self:
        q = self.get_q_available_now()
        q = (
            (
                (q & models.Q(type_id=settings.PK_MEDNUM_FORMATION_TYPE))
                | self.for_attendant_q(attendant)
            )
            if attendant.conseiller_numerique
            else (q | self.for_attendant_q(attendant))
        )

        return (
            self.annotate(attendants_count=Count("attendants"))
            .filter(q)
            .order_by("start_datetime")
            .distinct()
        )

    def for_attendant(self, attendant: HabilitationRequest) -> Self:
        return self.filter(self.for_attendant_q(attendant))

    def register_attendant(self, attendant: HabilitationRequest) -> None:
        for formation in self.values_list("pk", flat=True):
            FormationAttendant.objects.get_or_create(
                formation_id=formation, attendant_id=attendant.pk
            )

    def unregister_attendant(self, attendant: HabilitationRequest) -> None:
        FormationAttendant.objects.filter(
            formation_id__in=self.values("pk"), attendant_id=attendant.pk
        ).delete()


class Formation(models.Model):
    class Status(models.IntegerChoices):
        PRESENTIAL = (auto(), "En présentiel")
        REMOTE = (auto(), "À distance")

    class State(models.IntegerChoices):
        ACTIVE = (auto(), "Active")
        CANCELLED = (auto(), "Annulé")

    start_datetime = models.DateTimeField("Date et heure de début de la formation")
    end_datetime = models.DateTimeField(
        "Date et heure de fin de la formation", null=True, blank=True
    )
    duration = models.IntegerField("Durée en heures")
    max_attendants = models.IntegerField("Nombre maximum d'inscrits possibles")
    status = models.IntegerField("En présentiel/à distance", choices=Status.choices)
    state = models.IntegerField(
        "État de la formation", choices=State.choices, default=State.ACTIVE
    )
    place = models.CharField("Lieu", max_length=500, blank=True, default="Distanciel")
    type = models.ForeignKey(FormationType, on_delete=models.PROTECT)
    intra = models.BooleanField("Session intra", default=False)

    description = models.TextField("Description", blank=True, default="")
    id_grist = models.CharField(
        "Id Grist", editable=False, max_length=50, blank=True, default=""
    )
    organisation = models.ForeignKey(
        FormationOrganization,
        on_delete=models.PROTECT,
        null=True,
        default=None,
        related_name="formations",
    )

    objects = FormationQuerySet.as_manager()

    @property
    def number_of_attendants(self):
        return self.attendants.count()

    @property
    def date_range_str(self):
        if self.end_datetime:
            return (
                f"Du {date(self.start_datetime, 'd F Y à H:i')} "
                f"au {date(self.end_datetime, 'd F Y à H:i')}"
            )
        else:
            if self.start_datetime.hour in (0, 1, 2):
                return f"Début le {date(self.start_datetime, 'd F Y')} "
            return f"Début le {date(self.start_datetime, 'd F Y à H:i')} "

    def __str__(self):
        return f"{self.type.label} {self.date_range_str.casefold()}"

    def register_attendant(self, attendant: HabilitationRequest):
        Formation.objects.filter(pk=self.pk).register_attendant(attendant)

    def unregister_attendant(self, attendant: HabilitationRequest):
        Formation.objects.filter(pk=self.pk).unregister_attendant(attendant)

    class Meta:
        verbose_name = "Formation aidant"
        verbose_name_plural = "Formations aidant"
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_datetime__lte=models.F("end_datetime")),
                name="must_starts_before_or_equal_it_ends",
            ),
            models.CheckConstraint(
                check=models.Q(duration__gt=0), name="must_be_a_non_0_duration"
            ),
            models.CheckConstraint(
                check=models.Q(max_attendants__gt=0), name="cant_have_0_max_attendants"
            ),
        ]


class FormationAttendant(models.Model):
    State = FormationAttendantState

    created_at = models.DateTimeField("Date création", auto_now_add=True, null=True)
    updated_at = models.DateTimeField("Date modification", auto_now=True, null=True)

    attendant = models.ForeignKey(
        "aidants_connect_web.HabilitationRequest",
        on_delete=models.CASCADE,
        related_name="formations",
    )

    formation = models.ForeignKey(
        Formation, on_delete=models.PROTECT, related_name="attendants"
    )
    organization_warned_at = models.DateTimeField(
        "Lʼorganisation de la formation a été informée "
        "de lʼinscription de cette personne à…",
        null=True,
        default=None,
    )
    id_grist = models.CharField(
        "Id Grist", editable=False, max_length=50, blank=True, default=""
    )

    state = models.IntegerField(
        "État de la demande", choices=State.choices, default=State.DEFAULT
    )

    class Meta:
        verbose_name = "Formation : inscrit"
        verbose_name_plural = "Formation : inscrits"
        # One attendant a type can only be registered only once to a specific formation
        unique_together = ("attendant", "formation")
        triggers = [
            pgtrigger.Trigger(
                name="check_attendants_count",
                when=pgtrigger.Before,
                operation=pgtrigger.Insert,
                declare=[
                    ("attendants_count", "INTEGER"),
                    ("max_attendants_count", "INTEGER"),
                ],
                func=PGTriggerExtendedFunc(
                    f"""
                    -- prevent concurrent inserts from multiple transactions
                    LOCK TABLE {{meta.db_table}} IN EXCLUSIVE MODE;

                    SELECT INTO attendants_count COUNT(*)
                    FROM {{meta.db_table}}
                    WHERE {{columns.formation}} = NEW.{{columns.formation}}
                    AND {{columns.state}} != {FormationAttendantState.CANCELLED};

                    SELECT {{Formation_columns.max_attendants}} INTO max_attendants_count
                    FROM {{Formation_meta.db_table}}
                    WHERE {{Formation_meta.pk.name}} = NEW.{{columns.formation}};

                    IF attendants_count >= max_attendants_count THEN
                        RAISE EXCEPTION 'Formation is already full.' USING ERRCODE = 'check_violation';
                    END IF;

                    RETURN NEW;
                    """,  # noqa: E501, W291
                    additionnal_models={"Formation": Formation},
                ),
            )
        ]


class IdGenerator(models.Model):
    code = models.CharField(max_length=100, unique=True)
    last_id = models.PositiveIntegerField()
