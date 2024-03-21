from __future__ import annotations

from datetime import timedelta
from enum import auto
from typing import TYPE_CHECKING, Any, Self

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import CASCADE, Count
from django.template.defaultfilters import date
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.timezone import now

import pgtrigger

from aidants_connect_common.utils import PGTriggerExtendedFunc, render_markdown
from aidants_connect_pico_cms.fields import MarkdownField

if TYPE_CHECKING:
    from aidants_connect_habilitation.models import AidantRequest
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


class FormationQuerySet(models.QuerySet):
    def for_attendant_q(self, attendant: HabilitationRequest | AidantRequest):
        return models.Q(
            attendants__attendant_id=attendant.pk,
            attendants__attendant_content_type=ContentType.objects.get_for_model(
                attendant._meta.model
            ),
        )

    def available_for_attendant(
        self, after: timedelta, attendant: HabilitationRequest | AidantRequest
    ) -> Self:
        return self.annotate(attendants_count=Count("attendants")).filter(
            models.Q(
                attendants_count__lt=models.F("max_attendants"),
                start_datetime__gte=now() + after,
            )
            | self.for_attendant_q(attendant)
        )

    def for_attendant(self, attendant: HabilitationRequest | AidantRequest) -> Self:
        return self.filter(self.for_attendant_q(attendant))

    def register_attendant(
        self, attendant: HabilitationRequest | AidantRequest
    ) -> None:
        FormationAttendant.objects.bulk_create(
            [
                FormationAttendant(
                    formation_id=formation,
                    attendant_id=attendant.pk,
                    attendant_content_type=ContentType.objects.get_for_model(
                        attendant._meta.model
                    ),
                )
                for formation in self.values_list("pk", flat=True)
            ],
            ignore_conflicts=True,
        )

    def unregister_attendant(
        self, attendant: HabilitationRequest | AidantRequest
    ) -> None:
        FormationAttendant.objects.filter(
            formation_id__in=self.values("pk"),
            attendant_id=attendant.pk,
            attendant_content_type=ContentType.objects.get_for_model(
                attendant._meta.model
            ),
        ).delete()


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

    objects = FormationQuerySet.as_manager()

    @property
    def number_of_attendants(self):
        return self.attendants.count()

    @property
    def date_range_str(self):
        return (
            f"Du {date(self.start_datetime, 'd F Y à H:i')} "
            f"au {date(self.end_datetime, 'd F Y à H:i')}"
        )

    def __str__(self):
        return f"{self.type.label} {self.date_range_str.casefold()}"

    def register_attendant(self, attendant: HabilitationRequest | AidantRequest):
        Formation.objects.filter(pk=self.pk).register_attendant(attendant)

    def unregister_attendant(self, attendant: HabilitationRequest | AidantRequest):
        Formation.objects.filter(pk=self.pk).unregister_attendant(attendant)

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

    @cached_property
    def target(self):
        return self.attendant_content_type.get_object_for_this_type(
            pk=self.attendant_id
        )

    def __str__(self):
        return f"{self.target}"

    class Meta:
        verbose_name = "Formation : inscrit"
        verbose_name_plural = "Formation : inscrits"
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
                func=PGTriggerExtendedFunc(
                    """
                    -- prevent concurrent inserts from multiple transactions
                    LOCK TABLE {meta.db_table} IN EXCLUSIVE MODE;

                    SELECT INTO attendants_count COUNT(*) 
                    FROM {meta.db_table}
                    WHERE {columns.formation} = NEW.{columns.formation};

                    SELECT {Formation_columns.max_attendants} INTO max_attendants_count
                    FROM {Formation_meta.db_table} 
                    WHERE {Formation_meta.pk.name} = NEW.{columns.formation};

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
