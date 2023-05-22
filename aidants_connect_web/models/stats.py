from __future__ import annotations

import logging

from django.db import models

logger = logging.getLogger()


class AidantStatistiques(models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True, null=True)
    number_aidants = models.PositiveIntegerField("Nb d'aidant", default=0)
    number_aidants_is_active = models.PositiveIntegerField(
        "Nb d'aidant 'actif au sens django' ", default=0
    )
    number_responsable = models.PositiveIntegerField("Nb de responsable", default=0)
    number_aidants_without_totp = models.PositiveIntegerField(
        "Nb d'aidant sans carte TOTP ", default=0
    )
    number_aidant_can_create_mandat = models.PositiveIntegerField(
        "Nb d'aidant pouvant créer des mandats", default=0
    )
    number_aidant_with_login = models.PositiveIntegerField(
        "Nb d'aidant pouvant créer des mandats et s'étant connecté", default=0
    )
    number_aidant_who_have_created_mandat = models.PositiveIntegerField(
        "Nb d'aidant qui ont créé des mandats", default=0
    )

    class Meta:
        verbose_name = "Statistiques aidants"
        verbose_name_plural = "Statistiques aidants"
