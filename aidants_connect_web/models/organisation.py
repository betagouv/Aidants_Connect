from __future__ import annotations

import logging
from uuid import uuid4

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import SET_NULL, Q, QuerySet, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.functional import cached_property

from aidants_connect_common.models import Department
from aidants_connect_erp.models import CardSending

from .journal import Journal
from .utils import delete_mandats_and_clean_journal

logger = logging.getLogger()


def get_staff_organisation_name_id() -> int:
    try:
        return Organisation.objects.get(name=settings.STAFF_ORGANISATION_NAME).pk
    except Organisation.DoesNotExist:
        return 1


class OrganisationType(models.Model):
    name = models.CharField("Nom", max_length=350)

    def __str__(self):
        return f"{self.name}"


class OrganisationManager(models.Manager):
    def accredited(self):
        return self.filter(
            aidants__is_active=True,
            aidants__can_create_mandats=True,
            aidants__carte_totp__isnull=False,
            is_active=True,
        ).distinct()

    def not_yet_accredited(self):
        return self.filter(
            aidants__is_active=True,
            aidants__can_create_mandats=True,
            aidants__carte_totp__isnull=True,
            is_active=True,
        ).distinct()

    def having_formation_unregistered_habilitation_requests(self):
        return self.filter(
            is_active=True,
            habilitation_requests__isnull=False,
            habilitation_requests__formations=None,
        ).distinct()


def organisation_allowed_demarches():
    return list(settings.DEMARCHES.keys())


class Organisation(models.Model):
    legal_category = models.PositiveIntegerField(
        "categorieJuridiqueUniteLegale", default=0
    )
    siren = models.BigIntegerField("N° SIREN", default=1)

    legal_cat_level_one = models.CharField(
        "Niveau I catégories juridiques", max_length=255, null=True
    )
    legal_cat_level_two = models.CharField(
        "Niveau II catégories juridiques", max_length=255, null=True
    )
    legal_cat_level_three = models.CharField(
        "Niveau III catégories juridiques", max_length=255, null=True
    )

    data_pass_id = models.PositiveIntegerField("Datapass ID", null=True, unique=True)
    uuid = models.UUIDField("API ID", unique=True, default=uuid4)
    name = models.TextField("Nom", default="No name provided")
    type = models.ForeignKey(
        OrganisationType, null=True, blank=True, on_delete=SET_NULL
    )
    is_experiment = models.BooleanField("Structure d'expérimentation ?", default=False)
    siret = models.BigIntegerField("N° SIRET", default=1)
    address = models.TextField("Adresse", default="No address provided")
    zipcode = models.CharField("Code Postal", max_length=10, default="0")
    city = models.CharField("Ville", max_length=255, null=True)

    city_insee_code = models.CharField(
        "Code INSEE de la ville", max_length=5, null=True, blank=True
    )

    department_insee_code = models.CharField(
        "Code INSEE du département", max_length=5, null=True, blank=True
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

    allowed_demarches = ArrayField(
        models.CharField(
            max_length=16,
            choices=(
                (name, attributes["titre"])
                for name, attributes in settings.DEMARCHES.items()
            ),
        ),
        default=organisation_allowed_demarches,
    )

    is_active = models.BooleanField("Est active", default=True, editable=False)

    created_at = models.DateTimeField("Date création", auto_now_add=True)
    updated_at = models.DateTimeField("Date modification", auto_now=True)

    created_by_fne = models.BooleanField("Création FNE", default=False)
    id_fne = models.CharField(
        "ID FNE", max_length=255, null=True, blank=True, editable=False
    )

    objects = OrganisationManager()

    def __str__(self):
        return f"{self.name}"

    class AlreadyExists(Exception):
        pass

    @cached_property
    def region(self):
        try:
            return Department.objects.get(insee_code=self.department_insee_code).region
        except Exception:
            return None

    @cached_property
    def num_active_aidants(self):
        return self.aidants.active().count()

    num_active_aidants.short_description = "Nombre d'aidants actifs"

    def admin_num_active_aidants(self):
        return self.num_active_aidants

    @cached_property
    def num_cards_used(self):
        from .mandat import CarteTOTP

        return CarteTOTP.objects.filter(aidant__in=self.aidants.all()).count()

    num_cards_used.short_description = "Nombre de cartes utilisées par un aidant"

    @cached_property
    def num_mandats(self):
        return self.mandats.count()

    def admin_num_mandats(self):
        return self.num_mandats

    admin_num_mandats.short_description = "Nombre de mandats"

    @cached_property
    def num_active_mandats(self):
        return (
            self.mandats.filter(
                expiration_date__gte=timezone.now(),
                autorisations__revocation_date__isnull=True,
            )
            .distinct()
            .count()
        )

    @cached_property
    def aidants_not_responsables(self) -> QuerySet:
        return self.aidants.exclude(responsable_de=self)

    @cached_property
    def responsables_is_active(self) -> QuerySet:
        return self.responsables.exclude(is_active=False)

    @cached_property
    def num_usagers(self):
        return self.mandats.distinct("usager").count()

    @cached_property
    def num_demarches(self):
        return Journal.objects.find_demarches_for_organisation(self).count()

    @cached_property
    def num_received_cards(self):
        return CardSending.get_cards_stock_for_one_organisation(self)

    def admin_num_received_cards(self):
        return self.num_received_cards

    admin_num_received_cards.short_description = "Nombre de cartes reçues"

    @cached_property
    def referents_eligible_aidants(self):
        return self.aidants.exclude(
            Q(responsable_de=self) | Q(is_active=False)
        ).order_by("last_name")

    @property
    def display_address(self):
        return self.address if self.address != "No address provided" else "__________"

    @property
    def display_city(self):
        return self.city if self.city else "__________"

    def set_empty_zipcode_from_address(self):
        if self.zipcode != "0":
            return
        adr = self.address
        if adr:
            try:
                without_city = adr.rpartition(" ")[0]
                zipcode = without_city.rsplit(" ")[-1]
                if zipcode.isdigit():
                    self.zipcode = zipcode
                    self.save()
            except Exception:
                pass

    def deactivate_organisation(self):
        self.is_active = False
        self.save()
        for aidant in self.aidants.all():
            aidant.remove_from_organisation(self)

    def activate_organisation(self):
        self.is_active = True
        self.save()

    def clean_journal_entries_and_delete_mandats(self, request=None):
        today = timezone.now()
        str_today = today.strftime("%d/%m/%Y à %Hh%M")
        delete_mandats_and_clean_journal(self, str_today)

        # we need migrate aidants before delete organisations
        if self.aidants.count() > 0:
            if request:
                django_messages.error(
                    request,
                    "Vous ne pouvez pas supprimer une organisation avec des aidants.",
                )
            return False

        entries = Journal.objects.filter(organisation=self)

        organisation_str_add_inf = (
            f"Add by clean_journal_entries_and_delete_mandats :"
            f"\n Relatif à l'organisation supprimée {self.name} "
            f"{self.data_pass_id}  {self.type} "
            f"{self.siret} le {str_today}"
        )
        entries.update(
            organisation=None,
            additional_information=Concat(
                "additional_information", Value(organisation_str_add_inf)
            ),
        )
        return True
