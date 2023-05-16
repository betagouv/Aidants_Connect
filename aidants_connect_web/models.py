from __future__ import annotations

import logging
from datetime import datetime, timedelta
from os import walk as os_walk
from os.path import dirname
from os.path import join as path_join
from re import sub as regex_sub
from typing import Collection, Iterable, Optional, Union

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import ArrayField
from django.db import IntegrityError, models, transaction
from django.db.models import SET_NULL, Q, QuerySet, Value
from django.db.models.functions import Concat
from django.dispatch import Signal
from django.template import defaultfilters, loader
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from django_otp.plugins.otp_totp.models import TOTPDevice
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import PhoneNumber, PhoneNumberFormat, format_number, is_valid_number
from phonenumbers import parse as parse_number
from phonenumbers import region_code_for_country_code

from aidants_connect_common.models import Department
from aidants_connect_common.utils.constants import (
    JOURNAL_ACTIONS,
    AuthorizationDurationChoices,
    AuthorizationDurations,
    JournalActionKeywords,
)
from aidants_connect_web.constants import NotificationType, RemoteConsentMethodChoices
from aidants_connect_web.utilities import (
    generate_attestation_hash,
    mandate_template_path,
)

logger = logging.getLogger()


def delete_mandats_and_clean_journal(item, str_today):
    for mandat in item.mandats.all():
        entries = Journal.objects.filter(mandat=mandat)
        mandat_str_add_inf = (
            f"Added by clean_journal_entries_and_delete_mandats :"
            f"\n Relatif au mandat supprimé {mandat} le {str_today}"
        )
        entries.update(
            mandat=None,
            additional_information=Concat(
                "additional_information", Value(mandat_str_add_inf)
            ),
        )
        mandat.delete()


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


class Organisation(models.Model):
    data_pass_id = models.PositiveIntegerField("Datapass ID", null=True, unique=True)
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

    is_active = models.BooleanField("Est active", default=True, editable=False)

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

    def admin_num_active_aidants(self):
        return self.num_active_aidants

    admin_num_active_aidants.short_description = "Nombre d'aidants actifs"

    @cached_property
    def num_mandats(self):
        return self.mandats.count()

    def admin_num_mandats(self):
        return self.num_mandats

    @cached_property
    def num_active_mandats(self):
        return (
            Mandat.objects.filter(
                expiration_date__gte=timezone.now(),
                organisation=self,
                autorisations__revocation_date__isnull=True,
            )
            .distinct()
            .count()
        )

    @cached_property
    def aidants_not_responsables(self) -> QuerySet:
        return self.aidants.exclude(responsable_de=self)

    @cached_property
    def num_usagers(self):
        return Mandat.objects.filter(organisation=self).distinct("usager").count()

    @property
    def display_address(self):
        return self.address if self.address != "No address provided" else ""

    admin_num_mandats.short_description = "Nombre de mandats"

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


class AidantManager(UserManager):
    def active(self):
        return self.filter(is_active=True)

    def __normalize_fields(self, extra_fields: dict):
        for field_name in extra_fields.keys():
            field = self.model._meta.get_field(field_name)
            field_value = extra_fields[field_name]

            if field.many_to_many and isinstance(field_value, str):
                extra_fields[field_name] = [pk.strip() for pk in field_value.split(",")]
            if field.many_to_one and not isinstance(
                field_value, field.remote_field.model
            ):
                field_value = (
                    int(field_value)
                    if not isinstance(field_value, int)
                    else field_value
                )
                extra_fields[field_name] = field.remote_field.model(field_value)

    def create_user(self, username, email=None, password=None, **extra_fields):
        self.__normalize_fields(extra_fields)
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        self.__normalize_fields(extra_fields)
        return super().create_superuser(username, email, password, **extra_fields)

    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).lower()

    def create(self, **kwargs):
        if email := kwargs.get("email"):
            email = email.strip().lower()
            kwargs["email"] = email
            if (
                username := kwargs.get("username")
            ) and username.strip().lower() == email:
                kwargs["username"] = email

        return super().create(**kwargs)


aidants__organisations_changed = Signal()


class AidantType(models.Model):
    name = models.CharField("Nom", max_length=350)

    def __str__(self):
        return f"{self.name}"


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
    phone = models.TextField("Téléphone", blank=True)

    aidant_type = models.ForeignKey(
        AidantType,
        on_delete=models.SET_NULL,
        verbose_name="Type d'aidant",
        null=True,
        blank=True,
    )

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        verbose_name="Organisation courante",
        related_name="current_aidants",
    )
    organisations = models.ManyToManyField(
        Organisation,
        verbose_name="Membre des organisations",
        related_name="aidants",
    )
    responsable_de = models.ManyToManyField(
        Organisation, related_name="responsables", blank=True
    )
    can_create_mandats = models.BooleanField(
        default=True,
        verbose_name="Aidant - Peut créer des mandats",
        help_text=(
            "Précise si l’utilisateur peut accéder à l’espace aidant "
            "pour créer des mandats."
        ),
    )
    validated_cgu_version = models.TextField(null=True)

    created_at = models.DateTimeField("Date de création", auto_now_add=True, null=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True, null=True)

    objects = AidantManager()

    REQUIRED_FIELDS = AbstractUser.REQUIRED_FIELDS + ["organisation"]

    class Meta:
        verbose_name = "aidant"

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.organisations.add(self.organisation)

    def get_full_name(self):
        return str(self)

    def get_valid_autorisation(self, demarche, usager):
        """
        :param demarche:
        :param usager:
        :return: Autorisation object if this aidant may perform the specified `demarche`
        for the specified `usager`, `None` otherwise.`
        """
        try:
            return (
                Autorisation.objects.active()
                .for_demarche(demarche)
                .for_usager(usager)
                .visible_by(self)
                .get()
            )
        except Autorisation.DoesNotExist:
            return None

    def get_usagers(self):
        """
        :return: a queryset of usagers who have at least one autorisation
        (active or expired) with the aidant's organisation.
        """
        return Usager.objects.visible_by(self).distinct()

    def get_usager(self, usager_id):
        """
        :return: an usager or `None` if the aidant isn't allowed
        by an autorisation to access this usager.
        """
        try:
            return self.get_usagers().get(pk=usager_id)
        except Usager.DoesNotExist:
            return None

    def get_usagers_with_active_autorisation(self):
        """
        :return: a queryset of usagers who have an active autorisation
        with the aidant's organisation.
        """
        active_mandats = Mandat.objects.filter(organisation=self.organisation).active()
        user_list = active_mandats.values_list("usager", flat=True)
        return Usager.objects.filter(pk__in=user_list)

    def get_autorisations(self):
        """
        :return: a queryset of autorisations visible by this aidant.
        """
        return Autorisation.objects.visible_by(self).distinct()

    def get_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's autorisations.
        """
        return self.get_autorisations().for_usager(usager)

    def get_active_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's active autorisations
        that are visible by this aidant.
        """
        return self.get_autorisations_for_usager(usager).active()

    def get_inactive_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's inactive (expired or revoked)
        autorisations that are visible by this aidant.
        """
        return self.get_autorisations_for_usager(usager).inactive()

    def get_active_demarches_for_usager(self, usager):
        """
        :param usager:
        :return: a list of demarches the usager has active autorisations for
        in this aidant's organisation.
        """
        return self.get_active_autorisations_for_usager(usager).values_list(
            "demarche", flat=True
        )

    def get_last_action_timestamp(self):
        """
        :return: the timestamp of this aidant's last logged action or `None`.
        """
        try:
            return Journal.objects.filter(aidant=self).last().creation_date
        except AttributeError:
            return None

    def get_journal_create_attestation(self, access_token):
        """
        :return: the corresponding 'create_attestation' Journal entry initiated
        by the aidant
        """
        journal_create_attestation = Journal.objects.filter(
            aidant=self,
            action=JournalActionKeywords.CREATE_ATTESTATION,
            access_token=access_token,
        ).last()
        return journal_create_attestation

    def is_in_organisation(self, organisation: Organisation):
        return self.organisations.filter(pk=organisation.id).exists()

    def is_responsable_structure(self):
        """
        :return: True if the Aidant is responsable of at least one organisation
        """
        return self.responsable_de.count() >= 1

    def can_see_aidant(self, aidant):
        """
        :return: True if the current object is responsible for at least one of aidant's
        organisations
        """
        respo_orgas = self.responsable_de.all()
        aidant_orgas = aidant.organisations.all()
        return any(org in respo_orgas for org in aidant_orgas)

    def must_validate_cgu(self):
        return self.validated_cgu_version != settings.CGU_CURRENT_VERSION

    @cached_property
    def has_a_totp_device(self):
        return self.totpdevice_set.filter(confirmed=True).exists()

    @cached_property
    def has_a_carte_totp(self) -> bool:
        return hasattr(self, "carte_totp")

    @cached_property
    def number_totp_card(self) -> str:
        if self.has_a_carte_totp:
            return self.carte_totp.serial_number
        return "Pas de Carte"

    def remove_from_organisation(self, organisation: Organisation) -> Optional[bool]:
        if not self.is_in_organisation(organisation):
            return None

        if self.organisations.count() == 1:
            self.is_active = False
            self.save()

            return self.is_active

        self.organisations.remove(organisation)
        if not self.is_in_organisation(self.organisation):
            self.organisation = self.organisations.order_by("id").first()
            self.save()

        aidants__organisations_changed.send(
            sender=self.__class__,
            instance=self,
            diff={"removed": [organisation], "added": []},
        )

        return self.is_active

    def set_organisations(self, organisations: Collection[Organisation]):
        if len(organisations) == 0:
            # Request to remove all organisation and add none
            raise ValueError("Can't remove all the organisations from aidant")

        current = set(self.organisations.all())
        future = set(organisations)
        to_remove = current - future
        to_add = future - current

        if len(to_add) == 0 and len(to_remove) == 0:
            # Nothing to do!
            return self.is_active

        if len(to_add) > 0:
            self.organisations.add(*to_add)
        if len(to_remove) > 0:
            self.organisations.remove(*to_remove)

        if not self.is_in_organisation(self.organisation):
            self.organisation = self.organisations.order_by("id").first()
            self.save()

        aidants__organisations_changed.send(
            sender=self.__class__,
            instance=self,
            diff={
                "removed": sorted(to_remove, key=lambda org: org.pk),
                "added": sorted(to_add, key=lambda org: org.pk),
            },
        )

        return self.is_active


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

    @transaction.atomic
    def validate_and_create_aidant(self):
        if self.status not in (
            self.STATUS_PROCESSING,
            self.STATUS_NEW,
            self.STATUS_WAITING_LIST_HABILITATION,
            self.STATUS_VALIDATED,
            self.STATUS_CANCELLED,
        ):
            return False

        if Aidant.objects.filter(username__iexact=self.email).count() > 0:
            aidant: Aidant = Aidant.objects.get(username__iexact=self.email)
            aidant.organisations.add(self.organisation)
            aidant.is_active = True
            aidant.can_create_mandats = True
            aidant.save()
            self.status = self.STATUS_VALIDATED
            self.save()
            return True

        Aidant.objects.create(
            last_name=self.last_name,
            first_name=self.first_name,
            profession=self.profession,
            organisation=self.organisation,
            email=self.email,
            username=self.email,
        )
        self.status = self.STATUS_VALIDATED
        self.save()
        return True

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status]

    @property
    def origin_label(self):
        return self.ORIGIN_LABELS[self.origin]


class UsagerQuerySet(models.QuerySet):
    def active(self):
        return (
            self.filter(mandats__expiration_date__gt=timezone.now())
            .filter(mandats__autorisations__revocation_date__isnull=True)
            .distinct()
        )

    def visible_by(self, aidant):
        """
        :param aidant:
        :return: a new QuerySet instance only filtering in the usagers who have
        an autorisation with this aidant's organisation.
        """
        return self.filter(mandats__organisation=aidant.organisation).distinct()


class Usager(models.Model):
    GENDER_FEMALE = "female"
    GENDER_MALE = "male"
    GENDER_CHOICES = (
        (GENDER_FEMALE, "Femme"),
        (GENDER_MALE, "Homme"),
    )
    BIRTHCOUNTRY_FRANCE = "99100"
    EMAIL_NOT_PROVIDED = "noemailprovided@aidantconnect.beta.gouv.fr"

    given_name = models.CharField("Prénom", max_length=255, blank=False)
    family_name = models.CharField("Nom", max_length=255, blank=False)
    preferred_username = models.CharField(max_length=255, blank=True, null=True)

    gender = models.CharField(
        "Genre",
        max_length=6,
        choices=GENDER_CHOICES,
        default=GENDER_FEMALE,
    )

    birthdate = models.DateField("Date de naissance", blank=False)
    birthplace = models.CharField(
        "Lieu de naissance", max_length=5, blank=True, null=True
    )
    birthcountry = models.CharField(
        "Pays de naissance",
        max_length=5,
        default=BIRTHCOUNTRY_FRANCE,
    )

    sub = models.TextField(blank=False, unique=True)
    email = models.EmailField(blank=False, default=EMAIL_NOT_PROVIDED)
    creation_date = models.DateTimeField("Date de création", default=timezone.now)

    phone = PhoneNumberField(blank=True)

    objects = UsagerQuerySet.as_manager()

    class Meta:
        ordering = ["family_name", "given_name"]

    @property
    def search_terms(self):
        search_term = [self.family_name, self.given_name]
        if self.preferred_username:
            search_term.append(self.preferred_username)

        return search_term

    @property
    def renew_mandate_url(self):
        return reverse("renew_mandat", kwargs={"usager_id": self.id})

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_full_name(self):
        return str(self)

    def normalize_birthplace(self):
        if not self.birthplace:
            return None

        normalized_birthplace = self.birthplace.zfill(5)
        if normalized_birthplace != self.birthplace:
            self.birthplace = normalized_birthplace
            self.save(update_fields=["birthplace"])

        return self.birthplace

    def clean_journal_entries_and_delete_mandats(self, request=None):
        today = timezone.now()
        str_today = today.strftime("%d/%m/%Y à %Hh%M")
        delete_mandats_and_clean_journal(self, str_today)

        entries = Journal.objects.filter(usager=self)

        usager_str_add_inf = (
            f"Add by clean_journal_entries_and_delete_mandats :"
            f"\n Relatif à l'usager supprimé {self.family_name} "
            f"{self.given_name}  {self.preferred_username} "
            f"{self.email} le {str_today}"
        )
        entries.update(
            usager=None,
            additional_information=Concat(
                "additional_information", Value(usager_str_add_inf)
            ),
        )
        return True

    def has_all_mandats_revoked_or_expired_over_a_year(self):
        for mandat in self.mandats.all():
            if (
                not mandat.was_explicitly_revoked
                and timezone.now() < mandat.expiration_date + timedelta(days=365)
            ):
                return False
        return True


def get_staff_organisation_name_id() -> int:
    try:
        return Organisation.objects.get(name=settings.STAFF_ORGANISATION_NAME).pk
    except Organisation.DoesNotExist:
        return 1


class MandatQuerySet(models.QuerySet):
    def exclude_outdated(self):
        return self.exclude(
            Q(expiration_date__lt=timezone.now() - timedelta(365))
            | Q(autorisations__revocation_date__lt=timezone.now() - timedelta(365))
        )

    def active(self):
        return (
            self.exclude(expiration_date__lt=timezone.now())
            .filter(autorisations__revocation_date__isnull=True)
            .distinct()
        )

    def inactive(self):
        return (
            self.exclude_outdated()
            .filter(
                Q(expiration_date__lt=timezone.now())
                | ~Q(autorisations__revocation_date__isnull=True)
            )
            .distinct()
        )

    def for_usager(self, usager):
        return self.filter(usager=usager)

    def renewable(self):
        return self.exclude_outdated().filter(
            ~Q(expiration_date__gt=timezone.now())
            | Q(autorisations__revocation_date__isnull=True)
        )


class Mandat(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        related_name="mandats",
        default=get_staff_organisation_name_id,
    )
    usager = models.ForeignKey(Usager, on_delete=models.PROTECT, related_name="mandats")
    creation_date = models.DateTimeField("Date de création", default=timezone.now)
    expiration_date = models.DateTimeField("Date d'expiration", default=timezone.now)
    duree_keyword = models.CharField(
        "Durée", max_length=16, choices=AuthorizationDurationChoices.choices, null=True
    )

    is_remote = models.BooleanField("Signé à distance ?", default=False)
    consent_request_id = models.CharField(max_length=36, blank=True, default="")
    remote_constent_method = models.CharField(
        "Méthode de consentement à distance",
        choices=RemoteConsentMethodChoices.model_choices,
        blank=True,
        max_length=200,
    )

    template_path = models.TextField(
        "Template utilisé",
        null=True,
        blank=False,
        default=mandate_template_path,
        editable=False,
    )

    objects = MandatQuerySet.as_manager()

    def __str__(self):
        return f"#{self.id}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expiration_date

    @property
    def is_active(self):
        if self.is_expired:
            return False
        # A `mandat` is considered `active` if it contains
        # at least one active `autorisation`.
        return self.autorisations.active().exists()

    @property
    def can_renew(self):
        return (
            not self.is_expired or self.objects.renewable().filter(mandat=self).exists()
        )

    @cached_property
    def revocation_date(self) -> Optional[datetime]:
        """
        Returns the date of the most recently revoked authorization if all them
        were revoked, ``None``, otherwise.
        """
        return (
            self.autorisations.order_by("-revocation_date").first().revocation_date
            if self.was_explicitly_revoked and self.autorisations.exists()
            else None
        )

    @cached_property
    def template_repr(self):
        """Defines a stadard way to represent a Mandat in templates"""
        creation_date_repr = (
            f" le {defaultfilters.date(self.creation_date)}"
            if self.creation_date
            else ""
        )
        duree_keyword_repr = (
            f" pour une durée de {self.get_duree_keyword_display()}"
            if self.duree_keyword
            else ""
        )
        return f"signé avec {self.usager}{creation_date_repr}{duree_keyword_repr}"

    @cached_property
    def was_explicitly_revoked(self) -> bool:
        """
        Returns whether the mandate was explicitely revoked, independently of it's
        expiration date.
        """
        return not self.autorisations.exclude(revocation_date__isnull=False)

    def get_absolute_url(self):
        path = reverse("mandat_visualisation", kwargs={"mandat_id": self.pk})
        url = regex_sub(r"/+", "/", f"{settings.HOST}{path}")
        return f"https://{url}"

    def get_mandate_template_path(self) -> str | None:
        """Returns the template file path of the consent document that was presented
        to the user when the mandate was issued.

        :return: the template file relative path as can be used on Django's
        template engine (without `templates` prepended), otherwise `None`
        """
        return (
            self.template_path
            if self.template_path is not None
            else self._get_mandate_template_path_from_journal_hash()
        )

    def _get_mandate_template_path_from_journal_hash(self) -> Union[None, str]:
        """Legacy mode for `models.Mandat.text()`

        This will search which template file was used using the hash login in
        `models.Journal` entries and parse the template using it.

        :return: None when:
            - no log record could be found on this mandate
            - the original template file could not be found
        the template file relative path as can be used on Django's template engine
        (without `templates` prepended`) otherwise
        """

        journal_entries = Journal.find_attestation_creation_entries(self)

        if journal_entries.count() == 0:
            return None

        template_dir = dirname(
            loader.get_template(settings.MANDAT_TEMPLATE_PATH).origin.name
        )

        demarches = [it.demarche for it in self.autorisations.all()]

        for journal_entry in journal_entries:
            for _, _, filenames in os_walk(template_dir):
                for filename in filenames:
                    file_hash = generate_attestation_hash(
                        journal_entry.aidant,
                        self.usager,
                        demarches,
                        self.expiration_date,
                        journal_entry.creation_date.date().isoformat(),
                        path_join(settings.MANDAT_TEMPLATE_DIR, filename),
                    )

                    if file_hash == journal_entry.attestation_hash:
                        return path_join(settings.MANDAT_TEMPLATE_DIR, filename)

        return None

    def admin_is_active(self):
        return self.is_active

    admin_is_active.boolean = True
    admin_is_active.short_description = "is active"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if (
            self.remote_constent_method == RemoteConsentMethodChoices.SMS
            and not self.usager.phone
        ):
            raise IntegrityError("User phone must be set when remote consent is SMS")
        super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def get_attestation_or_none(cls, mandate_id):
        try:
            mandate = Mandat.objects.get(mandate_id)
            journal = Journal.find_attestation_creation_entries(mandate)
            # If the journal count is 1, let's use this, otherwise, we don't consider
            # the results to be sufficiently specific to display a hash
            if journal.count() == 1:
                return journal.first()
        except Exception:
            return None

    @classmethod
    def get_attestation_hash_or_none(cls, mandate_id) -> None | str:
        result = cls.get_attestation_or_none(mandate_id)
        return result.attestation_hash if result is not None else result

    @classmethod
    def find_soon_expired(cls, nb_days_before: int) -> QuerySet["Mandat"]:
        """Finds mandates that will be expired in less than `nb_days_before` days"""

        start = timezone.now()
        end = start + timedelta(days=nb_days_before)

        return cls.objects.filter(
            duree_keyword__in=(
                AuthorizationDurations.LONG,
                AuthorizationDurations.SEMESTER,
            ),
            expiration_date__range=(start, end),
        ).order_by("organisation", "expiration_date")

    @classmethod
    def transfer_to_organisation(cls, organisation: Organisation, ids: Collection[str]):
        failed_updates = []

        for mandate_id in ids:
            try:
                mandate = Mandat.objects.get(pk=mandate_id)
                journal = Mandat.get_attestation_or_none(mandate_id)

                with transaction.atomic():
                    mandate.organisation = organisation
                    mandate.save()

                    Journal.log_transfert_mandat(
                        mandate,
                        mandate.organisation,
                        getattr(journal, "attestation_hash", None),
                    )
                    if journal is not None:
                        journal.attestation_hash = generate_attestation_hash(
                            aidant=journal.aidant,
                            usager=mandate.usager,
                            demarches=journal.demarche,
                            expiration_date=mandate.expiration_date,
                            creation_date=mandate.expiration_date.date().isoformat(),
                            mandat_template_path=mandate.get_mandate_template_path(),
                            organisation_id=organisation.id,
                        )
                        journal.save()
            except Exception:
                failed_updates.append(mandate_id)
                logger.exception(
                    "An error happened while trying to transfer mandates to "
                    "another organisation"
                )

        return len(failed_updates) != 0, failed_updates

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(is_remote=False)
                    | (Q(is_remote=True) & ~Q(remote_constent_method=""))
                ),
                name="mandat_remote_mandate_method_set",
            ),
            # fmt: off
            models.CheckConstraint(
                check=(
                    ~Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                    | (
                        Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                        & ~Q(consent_request_id="")
                    )
                ),
                name="mandat_consent_request_id_set",
            ),
            # fmt: on
        ]


class AutorisationQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(mandat__expiration_date__lt=timezone.now()).filter(
            revocation_date__isnull=True
        )

    def inactive(self):
        return self.filter(
            Q(mandat__expiration_date__lt=timezone.now())
            | (
                Q(mandat__expiration_date__gt=timezone.now())
                & Q(revocation_date__isnull=False)
            )
        )

    def expired(self):
        return self.filter(mandat__expiration_date__lt=timezone.now())

    def revoked(self):
        return self.filter(
            Q(mandat__expiration_date__gt=timezone.now())
            & Q(revocation_date__isnull=False)
        )

    def for_usager(self, usager):
        return self.filter(mandat__usager=usager)

    def for_demarche(self, demarche):
        return self.filter(demarche=demarche)

    def visible_by(self, aidant):
        return self.filter(mandat__organisation=aidant.organisation)


class Autorisation(models.Model):
    DEMARCHE_CHOICES = [
        (name, attributes["titre"]) for name, attributes in settings.DEMARCHES.items()
    ]

    # Autorisation information
    mandat = models.ForeignKey(
        Mandat, null=True, on_delete=models.CASCADE, related_name="autorisations"
    )
    demarche = models.CharField(max_length=16, choices=DEMARCHE_CHOICES)

    # Autorisation expiration date management
    revocation_date = models.DateTimeField("Date de révocation", blank=True, null=True)

    # Journal entry creation information
    last_renewal_token = models.TextField(blank=False, default="No token provided")

    objects = AutorisationQuerySet.as_manager()

    def __str__(self):
        return f"#{self.id} {self.mandat} {self.mandat.usager} {self.demarche}"

    @cached_property
    def creation_date(self):
        return self.mandat.creation_date

    @cached_property
    def expiration_date(self):
        return self.mandat.expiration_date

    @cached_property
    def is_expired(self) -> bool:
        return self.mandat.is_expired

    @property
    def is_revoked(self) -> bool:
        return True if self.revocation_date else False

    @property
    def duration_for_humans(self) -> int:
        duration_for_computer = self.expiration_date - self.creation_date

        # We add one day so that duration is human-friendly.
        # i.e. for a human, there is one day between now and tomorrow at the same time,
        # and 0 for a computer.
        return duration_for_computer.days + 1

    @cached_property
    def was_separately_revoked(self) -> bool:
        """
        :return: `True` if the authorization's revocation date is considered
            different from the mandate's computed revocation date, `False` otherwise.
            **Notes:** The mandate's computed revocation date is the date of the most
            recently revoked authorization. The authorization's revocation date will be
            recently revoked authorization. The authorization's revocation date will be
            considered different if it was revoked outside a time window of 30 seconds
            around the mandate's computed reocation date. I.E., if it was revoked at
            least 15 seconds before or after the mandate.
        """
        if not self.is_revoked:
            return False

        if self.mandat.revocation_date is None:
            return True

        return abs(self.revocation_date - self.mandat.revocation_date) > timedelta(
            seconds=15
        )

    def revoke(self, aidant: Aidant, revocation_date=None):
        """
        revoke an autorisation and create the corresponding journal entry
        """
        if revocation_date is None:
            revocation_date = timezone.now()
        self.revocation_date = revocation_date
        self.save(update_fields=["revocation_date"])
        Journal.log_autorisation_cancel(self, aidant)


class ConnectionQuerySet(models.QuerySet):
    def expired(self):
        return self.filter(expires_on__lt=timezone.now())


def default_connection_expiration_date():
    now = timezone.now()
    return now + timedelta(seconds=settings.FC_CONNECTION_AGE)


class Connection(models.Model):
    state = models.TextField()  # FS
    nonce = models.TextField(default="No Nonce Provided")  # FS
    CONNECTION_TYPE = (("FS", "FC as FS"), ("FI", "FC as FI"))  # FS
    connection_type = models.CharField(
        max_length=2, choices=CONNECTION_TYPE, default="FI", blank=False
    )
    demarches = ArrayField(models.TextField(default="No démarche"), null=True)  # FS
    duree_keyword = models.CharField(
        "Durée", max_length=16, choices=AuthorizationDurationChoices.choices, null=True
    )
    mandat_is_remote = models.BooleanField(default=False)
    user_phone = PhoneNumberField(blank=True)
    consent_request_id = models.CharField(max_length=36, blank=True, default="")
    remote_constent_method = models.CharField(
        "Méthode de consentement à distance",
        choices=RemoteConsentMethodChoices.model_choices,
        blank=True,
        max_length=200,
    )

    usager = models.ForeignKey(
        Usager,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="connections",
    )  # FS

    expires_on = models.DateTimeField(default=default_connection_expiration_date)  # FS
    access_token = models.TextField(default="No token provided")  # FS

    code = models.TextField()
    demarche = models.TextField(default="No demarche provided")
    aidant = models.ForeignKey(
        Aidant,
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="connections",
    )
    organisation = models.ForeignKey(
        Organisation,
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="connections",
    )
    complete = models.BooleanField(default=False)
    autorisation = models.ForeignKey(
        Autorisation,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="connections",
    )

    objects = ConnectionQuerySet.as_manager()

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if (user_phone := self.user_phone) and isinstance(user_phone, PhoneNumber):
            # Test phone number is valid for provided region
            if not is_valid_number(user_phone):
                for region in set(settings.FRENCH_REGION_CODES) - {
                    region_code_for_country_code(self.user_phone.country_code)
                }:
                    parsed = parse_number(str(self.user_phone), region)
                    if is_valid_number(parsed):
                        user_phone = parsed
                        break
                else:
                    raise IntegrityError(
                        f"Phone number {user_phone} is not valid in any of the "
                        f"french region among {settings.FRENCH_REGION_CODES}"
                    )

            # Normalize phone number to international format
            self.user_phone = format_number(user_phone, PhoneNumberFormat.E164)
            if update_fields is not None:
                update_fields = {"user_phone"}.union(update_fields)

        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(aidant__isnull=True) & Q(organisation__isnull=True))
                    | (Q(aidant__isnull=False) & Q(organisation__isnull=False))
                ),
                name="aidant_and_organisation_set_together",
            ),
            models.CheckConstraint(
                check=(
                    Q(mandat_is_remote=False)
                    | (Q(mandat_is_remote=True) & ~Q(remote_constent_method=""))
                ),
                name="connection_remote_mandate_method_set",
            ),
            # fmt: off
            models.CheckConstraint(
                check=(
                    ~Q(remote_constent_method=RemoteConsentMethodChoices.SMS.name)
                    | (
                        Q(remote_constent_method=RemoteConsentMethodChoices.SMS.name)  # noqa: E501
                        & ~Q(user_phone="")
                    )
                ),
                name="connection_user_phone_set",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                    | (
                        Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                        & ~Q(consent_request_id="")
                    )
                ),
                name="connection_consent_request_id_set",
            ),
        ]
        verbose_name = "connexion"

    def __str__(self):
        return f"Connexion #{self.id} - {self.usager}"

    @property
    def is_expired(self):
        return self.expires_on < timezone.now()


class JournalQuerySet(models.QuerySet):
    def excluding_staff(self):
        return self.exclude(aidant__organisation__name=settings.STAFF_ORGANISATION_NAME)

    def has_user_explicitly_consented(
        self,
        user: Usager,
        aidant: Aidant,
        remote_constent_method: RemoteConsentMethodChoices,
        user_phone: str,
        consent_request_id: str,
    ) -> JournalQuerySet:
        return self.filter(
            action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            usager=user,
            aidant=aidant,
            remote_constent_method=remote_constent_method,
            is_remote_mandat=True,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        ).exists()

    def find_sms_consent_requests(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def find_sms_consent_recap(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def find_sms_user_consent(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def find_sms_user_consent_or_denial(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=[
                JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
                JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
            ],
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def _find_consent_actions(
        self,
        action: str | Collection,
        user_phone: PhoneNumber,
        consent_request_id: str | None = None,
    ):
        kwargs = {"user_phone": format_number(user_phone, PhoneNumberFormat.E164)}
        if isinstance(action, str):
            kwargs["action"] = action
        else:
            kwargs["action__in"] = list(action)
        if consent_request_id:
            kwargs["consent_request_id"] = consent_request_id

        return self.filter(**kwargs)


class Journal(models.Model):
    INFO_REMOTE_MANDAT = "Mandat conclu à distance pendant l'état d'urgence sanitaire (23 mars 2020)"  # noqa

    # mandatory
    action = models.CharField(max_length=30, choices=JOURNAL_ACTIONS, blank=False)
    aidant = models.ForeignKey(
        Aidant, on_delete=models.PROTECT, related_name="journal_entries", null=True
    )

    # automatic
    creation_date = models.DateTimeField(auto_now_add=True)

    # action dependant
    demarche = models.CharField(max_length=100, blank=True, null=True)
    usager = models.ForeignKey(
        Usager, null=True, on_delete=models.PROTECT, related_name="journal_entries"
    )
    duree = models.IntegerField(blank=True, null=True)  # En jours
    access_token = models.TextField(blank=True, null=True)
    autorisation = models.IntegerField(blank=True, null=True)
    attestation_hash = models.CharField(max_length=100, blank=True, null=True)
    additional_information = models.TextField(blank=True, null=True)

    is_remote_mandat = models.BooleanField(default=False)
    user_phone = PhoneNumberField(blank=True)
    consent_request_id = models.CharField(max_length=36, blank=True, default="")
    remote_constent_method = models.CharField(
        "Méthode de consentement à distance",
        choices=RemoteConsentMethodChoices.model_choices,
        blank=True,
        max_length=200,
    )
    mandat = models.ForeignKey(
        Mandat, null=True, on_delete=models.PROTECT, related_name="journal_entries"
    )

    organisation = models.ForeignKey(
        Organisation,
        null=True,
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )

    objects = JournalQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée de journal"
        verbose_name_plural = "entrées de journal"
        constraints = [
            # All infos are set when creating a journal for remote mandate by SMS
            models.CheckConstraint(
                check=(
                    ~Q(
                        action__in=[
                            JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
                            JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
                            JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
                            JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
                        ]
                    )
                    | (
                        Q(aidant__isnull=False)
                        & Q(is_remote_mandat=True)
                        & Q(user_phone__isnull_or_blank=False)
                        & Q(consent_request_id__isnull_or_blank=False)
                        & Q(remote_constent_method=RemoteConsentMethodChoices.SMS.name)
                        & Q(additional_information__isnull_or_blank=False)
                    )
                ),
                name="infos_set_remote_mandate_by_sms",
            )
        ]

    def __str__(self):
        return f"Entrée #{self.id} : {self.action} - {self.aidant}"

    def save(self, *args, **kwargs):
        if self.id:
            raise NotImplementedError("Editing is not allowed on journal entries")
        super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

    @classmethod
    def log_connection(cls, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.CONNECT_AIDANT,
        )

    @classmethod
    def log_activity_check(cls, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.ACTIVITY_CHECK_AIDANT,
        )

    @classmethod
    def log_card_association(cls, responsable: Aidant, aidant: Aidant, sn: str):
        more_info = f"aidant.id = {aidant.id}, sn = {sn}"
        return cls.objects.create(
            aidant=responsable,
            organisation=responsable.organisation,
            action=JournalActionKeywords.CARD_ASSOCIATION,
            additional_information=more_info,
        )

    @classmethod
    def log_card_validation(cls, responsable: Aidant, aidant: Aidant, sn: str):
        more_info = f"aidant.id = {aidant.id}, sn = {sn}"
        return cls.objects.create(
            aidant=responsable,
            organisation=responsable.organisation,
            action=JournalActionKeywords.CARD_VALIDATION,
            additional_information=more_info,
        )

    @classmethod
    def log_card_dissociation(
        cls, responsable: Aidant, aidant: Aidant, sn: str, reason: str
    ):
        more_info = f"aidant.id = {aidant.id}, sn = {sn}, reason = {reason}"
        return cls.objects.create(
            aidant=responsable,
            organisation=responsable.organisation,
            action=JournalActionKeywords.CARD_DISSOCIATION,
            additional_information=more_info,
        )

    @classmethod
    def log_franceconnection_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.FRANCECONNECT_USAGER,
        )

    @classmethod
    def log_update_email_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.UPDATE_EMAIL_USAGER,
        )

    @classmethod
    def log_update_phone_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.UPDATE_PHONE_USAGER,
        )

    @classmethod
    def log_init_renew_mandat(
        cls,
        aidant: Aidant,
        usager: Usager,
        demarches: list,
        duree: int,
        is_remote_mandat: bool,
        access_token: str,
        remote_constent_method: str,
        user_phone: str,
        consent_request_id: str,
    ):
        if is_remote_mandat and not remote_constent_method:
            raise IntegrityError(
                "remote_constent_method must be set when mandate is remote"
            )

        if (
            remote_constent_method in RemoteConsentMethodChoices.blocked_methods()
            and not consent_request_id
        ):
            raise IntegrityError(
                "consent_request_id must be set when mandate uses one of the following "
                f"consent methods {RemoteConsentMethodChoices.blocked_methods()}"
            )

        if (
            remote_constent_method == RemoteConsentMethodChoices.SMS.name
            and not user_phone
        ):
            raise IntegrityError(
                "user_phone must be set when " "mandate uses SMS consent method"
            )

        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.INIT_RENEW_MANDAT,
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            is_remote_mandat=is_remote_mandat,
            remote_constent_method=remote_constent_method,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    @classmethod
    def log_attestation_creation(
        cls,
        aidant: Aidant,
        usager: Usager,
        demarches: list,
        duree: int,
        is_remote_mandat: bool,
        access_token: str,
        attestation_hash: str,
        mandat: Mandat,
        remote_constent_method: str,
        user_phone: str,
        consent_request_id: str,
    ):
        if is_remote_mandat and not remote_constent_method:
            raise IntegrityError(
                "remote_constent_method must be set when mandate is remote"
            )

        if (
            remote_constent_method in RemoteConsentMethodChoices.blocked_methods()
            and not consent_request_id
        ):
            raise IntegrityError(
                "consent_request_id must be set when mandate uses one of the following "
                f"consent methods {RemoteConsentMethodChoices.blocked_methods()}"
            )

        if (
            remote_constent_method == RemoteConsentMethodChoices.SMS.name
            and not user_phone
        ):
            raise IntegrityError(
                "user_phone must be set when " "mandate uses SMS consent method"
            )

        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.CREATE_ATTESTATION,
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            attestation_hash=attestation_hash,
            mandat=mandat,
            is_remote_mandat=is_remote_mandat,
            remote_constent_method=remote_constent_method,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    @classmethod
    def log_autorisation_creation(cls, autorisation: Autorisation, aidant: Aidant):
        mandat = autorisation.mandat
        usager = mandat.usager

        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.CREATE_AUTORISATION,
            demarche=autorisation.demarche,
            duree=autorisation.duration_for_humans,
            autorisation=autorisation.id,
            is_remote_mandat=mandat.is_remote,
        )

    @classmethod
    def log_autorisation_use(
        cls,
        aidant: Aidant,
        usager: Usager,
        demarche: str,
        access_token: str,
        autorisation: Autorisation,
    ):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.USE_AUTORISATION,
            demarche=demarche,
            access_token=access_token,
            autorisation=autorisation.id,
        )

    @classmethod
    def log_autorisation_cancel(cls, autorisation: Autorisation, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=autorisation.mandat.usager,
            action=JournalActionKeywords.CANCEL_AUTORISATION,
            demarche=autorisation.demarche,
            duree=autorisation.duration_for_humans,
            autorisation=autorisation.id,
        )

    @classmethod
    def log_mandat_cancel(cls, mandat: Mandat, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=mandat.usager,
            action=JournalActionKeywords.CANCEL_MANDAT,
            mandat=mandat,
        )

    @classmethod
    def log_toitp_card_import(cls, aidant: Aidant, added: int, updated: int):
        message = f"{added} ajouts - {updated} modifications"
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.IMPORT_TOTP_CARDS,
            additional_information=message,
        )

    @classmethod
    def log_transfert_mandat(
        cls,
        mandat: Mandat,
        previous_organisation: Organisation,
        previous_hash: Optional[str],
    ):
        return cls.objects.create(
            mandat=mandat,
            organisation=mandat.organisation,
            action=JournalActionKeywords.TRANSFER_MANDAT,
            additional_information=(
                f"previous_organisation = {previous_organisation.pk}, "
                f"previous_hash = {previous_hash}"
            ),
        )

    @classmethod
    def find_attestation_creation_entries(cls, mandat: Mandat) -> QuerySet["Journal"]:
        # Let's first search by mandate
        journal = cls.objects.filter(
            action=JournalActionKeywords.CREATE_ATTESTATION, mandat=mandat
        )
        if journal.count() == 1:
            return journal

        # If the journal entry was created prior to this modification, there's no
        # association between the journal entry and the mandate so we need to search
        # using the naive heuristics
        start = mandat.creation_date - timedelta(hours=24)
        end = mandat.creation_date + timedelta(hours=24)
        return cls.objects.filter(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            usager=mandat.usager,
            aidant__organisation=mandat.organisation,
            creation_date__range=(start, end),
        )

    @classmethod
    def log_switch_organisation(cls, aidant: Aidant, previous: Organisation):
        more_info = (
            f"previous organisation : {previous.name} (#{previous.id}) -"
            f"new organisation : {aidant.organisation.name} (#{aidant.organisation.id})"
        )
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.SWITCH_ORGANISATION,
            additional_information=more_info,
        )

    @classmethod
    def log_user_consents_sms(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def log_user_denies_sms(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def log_user_mandate_recap_sms_sent(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def log_user_consent_request_sms_sent(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def _log_sms_event(
        cls,
        action: str,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        remote_constent_method = (
            RemoteConsentMethodChoices[remote_constent_method]
            if isinstance(remote_constent_method, str)
            else remote_constent_method
        )
        demarche = demarche if isinstance(demarche, str) else ",".join(demarche)
        duree = (
            AuthorizationDurations.duration(duree) if isinstance(duree, str) else duree
        )

        return cls.objects.create(
            action=action,
            aidant=aidant,
            demarche=demarche,
            duree=duree,
            remote_constent_method=remote_constent_method,
            is_remote_mandat=True,
            user_phone=format_number(user_phone, PhoneNumberFormat.E164),
            consent_request_id=consent_request_id,
            additional_information=f"message={message}",
        )


class CarteTOTP(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    seed = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    aidant = models.OneToOneField(
        Aidant, null=True, blank=True, on_delete=SET_NULL, related_name="carte_totp"
    )
    is_functional = models.BooleanField("Fonctionne correctement", default=True)

    @cached_property
    def totp_device(self):
        return TOTPDevice.objects.filter(user=self.aidant).first()

    class Meta:
        verbose_name = "carte TOTP"
        verbose_name_plural = "cartes TOTP"

    def __str__(self):
        return self.serial_number

    def createTOTPDevice(self, confirmed=False, tolerance=30):
        return TOTPDevice(
            key=self.seed,
            user=self.aidant,
            step=60,  # todo: some devices may have a different step!
            confirmed=confirmed,
            tolerance=tolerance,
            name=f"Carte n° {self.serial_number}",
        )


class IdGenerator(models.Model):
    code = models.CharField(max_length=100, unique=True)
    last_id = models.PositiveIntegerField()


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


class Notification(models.Model):
    type = models.CharField(choices=NotificationType.choices)
    aidant = models.ForeignKey(
        Aidant, on_delete=models.CASCADE, related_name="notifications"
    )
    date = models.DateField(auto_now_add=True)
    must_ack = models.BooleanField("Doit être acquité pour disparaître", default=True)
    auto_ack_date = models.DateField("Échéance", null=True, default=None)
    was_ack = models.BooleanField("A été acquité", null=True, default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    # Must be aknowlegeable if it has to be aknowleged
                    (Q(must_ack=False) ^ Q(was_ack__isnull=False))
                    # Can't both have no expiration date and be not acknoledgeable
                    & (Q(auto_ack_date__isnull=False) | Q(was_ack__isnull=False))
                ),
                name="must_ack_conditions",
            )
        ]
