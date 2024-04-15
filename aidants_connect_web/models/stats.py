from __future__ import annotations

import logging

from django.db import models

from aidants_connect_common.models import Department, Region
from aidants_connect_web.models import Aidant

logger = logging.getLogger()


class AbstractAidantStatistiques(models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True, null=True)
    number_aidants = models.PositiveIntegerField("Nb d'aidant", default=0)
    number_aidants_is_active = models.PositiveIntegerField(
        "Nb d'aidants 'actif au sens django' ", default=0
    )
    number_responsable = models.PositiveIntegerField("Nb de référent", default=0)

    number_aidant_can_create_mandat = models.PositiveIntegerField(
        "Nombre d’aidants formés et habilités (pouvant créer des mandats)", default=0
    )
    number_operational_aidants = models.PositiveIntegerField(
        "Nombre d’aidants opérationnels (nombre d’aidants formés, test Pix et carte reliée/activée) ",  # noqa
        default=0,
    )
    number_aidants_without_totp = models.PositiveIntegerField(
        "Nb d'aidants sans carte TOTP ", default=0
    )

    number_aidant_with_login = models.PositiveIntegerField(
        "Nb d'aidants pouvant créer des mandats et s'étant connecté", default=0
    )
    number_aidant_who_have_created_mandat = models.PositiveIntegerField(
        "Nb d'aidants qui ont créé des mandats", default=0
    )

    number_future_aidant = models.PositiveIntegerField(
        "Nombre d’aidants en cours d’habilitation", default=0
    )

    number_trained_aidant_since_begining = models.PositiveIntegerField(
        "Nb d'aidant formés depuis de le début (inactif compris)", default=0
    )

    number_future_trained_aidant = models.PositiveIntegerField(
        "Nombre d’aidants en cours d’habilitation ayant bénéficié de la formation AC",
        default=0,
    )

    number_organisation_requests = models.PositiveIntegerField(
        "Nombre de demandes d’habilitation de structures au total", default=0
    )

    number_validated_organisation_requests = models.PositiveIntegerField(
        "Nombre de validation de demandes d’habilitation de structures par l’équipe AC",
        default=0,
    )

    number_organisation_with_accredited_aidants = models.PositiveIntegerField(
        "Nombre de structures ayant des aidants habilités (formés, test Pix, au moins un aidant avec compte activé, carte activée)",  # noqa
        default=0,
    )  # noqa

    number_organisation_with_at_least_one_ac_usage = models.PositiveIntegerField(
        "Nombre de structures où il y a au moins une utilisation d’AC", default=0
    )

    number_usage_of_ac = models.PositiveIntegerField(
        "Nombre d’accompagnements réalisés via AC", default=0
    )

    number_orgas_in_zrr = models.PositiveIntegerField(
        "Nombre de structures classées en zone de revitalisation rurale", default=0
    )

    number_aidants_in_zrr = models.PositiveIntegerField(
        "Nombre d'aidant travaillant dans des stuctures classées en zone de revitalisation rurale",  # noqa
        default=0,
    )

    number_old_aidants_warned = models.PositiveIntegerField(
        "Nombre d'aidant actifs qui ne se sont pas connectés depuis longtemps et qui ont été alertés",  # noqa
        default=0,
    )

    number_old_inactive_aidants_warned = models.PositiveIntegerField(
        "Nombre d'aidant inactifs qui ne se sont pas connectés depuis longtemps et qui ont été alertés",  # noqa
        default=0,
    )

    number_aidants_with_otp_app = models.PositiveIntegerField(
        "Nombre d'aidant possédant une application TOTP",  # noqa
        default=0,
    )

    revoked_mandats = models.PositiveIntegerField("Nb mandats révoqués", default=0)

    class Meta:
        abstract = True
        verbose_name = "Statistiques aidants abstraite"
        verbose_name_plural = "Statistiques aidants abstraites"


class AidantStatistiques(AbstractAidantStatistiques):
    class Meta:
        verbose_name = "Statistiques aidants"
        verbose_name_plural = "Statistiques aidants"


class AidantStatistiquesbyRegion(AbstractAidantStatistiques):
    region = models.ForeignKey(
        Region, verbose_name="Région", editable=False, on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "Statistiques aidants par région"
        verbose_name_plural = "Statistiques aidants par région"


class AidantStatistiquesbyDepartment(AbstractAidantStatistiques):
    departement = models.ForeignKey(
        Department, verbose_name="Département", editable=False, on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "Statistiques aidants par département"
        verbose_name_plural = "Statistiques aidants par département"


class ReboardingAidantStatistiques(models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True, null=True)

    warning_date = models.DateTimeField(
        "Date de l'envoie de l'alerte", auto_now_add=True, null=True
    )
    reboarding_session_date = models.DateField("Date de la session de réembarquement")

    aidant = models.ForeignKey(
        Aidant, verbose_name="Aidant", editable=False, on_delete=models.PROTECT
    )

    connexions_before_reboarding = models.PositiveIntegerField(
        "Nb connexion avant réembarquement", default=0
    )

    connexions_j30_after = models.PositiveIntegerField(
        "Nb connexion J30 après réembarquement", default=0
    )
    connexions_j90_after = models.PositiveIntegerField(
        "Nb connexion J90 après réembarquement", default=0
    )

    created_mandats_before_reboarding = models.PositiveIntegerField(
        "Nb mandats créés avant réembarquement", default=0
    )
    created_mandats_j30_after = models.PositiveIntegerField(
        "Nb mandats créés J30 après réembarquement", default=0
    )
    created_mandats_j90_after = models.PositiveIntegerField(
        "Nb mandats créés J90 après réembarquement", default=0
    )

    demarches_before_reboarding = models.PositiveIntegerField(
        "Nb démarches avant réembarquement", default=0
    )
    demarches_j30_after = models.PositiveIntegerField(
        "Nb démarches J30 après réembarquement", default=0
    )
    demarches_j90_after = models.PositiveIntegerField(
        "Nb démarches J90 après réembarquement", default=0
    )

    usagers_before_reboarding = models.PositiveIntegerField(
        "Nb usagers accompagnés avant réembarquement", default=0
    )
    usagers_j30_after = models.PositiveIntegerField(
        "Nb usagers accompagnés J30 après réembarquement", default=0
    )
    usagers_j90_after = models.PositiveIntegerField(
        "Nb usagers accompagnés J90 après réembarquement", default=0
    )


class Meta:
    verbose_name = "Statistique réembarquement"
    verbose_name_plural = "Statistiques réembarquement"
