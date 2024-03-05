from __future__ import annotations

from enum import auto
from textwrap import dedent
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import CASCADE
from django.utils.safestring import mark_safe

import pgtrigger

from aidants_connect_common.utils import render_markdown
from aidants_connect_pico_cms.fields import MarkdownField


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


class IdGenerator(models.Model):
    code = models.CharField(max_length=100, unique=True)
    last_id = models.PositiveIntegerField()
