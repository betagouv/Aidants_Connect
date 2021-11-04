import logging
from datetime import timedelta, datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import Q, QuerySet, SET_NULL, CASCADE
from django.template import loader, defaultfilters
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django_otp.plugins.otp_totp.models import TOTPDevice
from typing import Union, Optional, Collection
from os import walk as os_walk
from os.path import join as path_join, dirname
from re import sub as regex_sub
from phonenumber_field.modelfields import PhoneNumberField

from aidants_connect_web.constants import (
    JOURNAL_ACTIONS,
    JournalActionKeywords,
    AuthorizationDurationChoices,
    AuthorizationDurations,
)
from aidants_connect_web.utilities import (
    generate_attestation_hash,
    mandate_template_path,
)


logger = logging.getLogger()


class OrganisationType(models.Model):
    name = models.CharField("Nom", max_length=350)

    def __str__(self):
        return f"{self.name}"


class Organisation(models.Model):
    data_pass_id = models.PositiveIntegerField("Datapass ID", null=True)
    name = models.TextField("Nom", default="No name provided")
    type = models.ForeignKey(
        OrganisationType, null=True, blank=True, on_delete=SET_NULL
    )
    siret = models.BigIntegerField("N° SIRET", default=1)
    address = models.TextField("Adresse", default="No address provided")
    zipcode = models.CharField("Code Postal", max_length=10, default="0")

    is_active = models.BooleanField("Est active", default=True, editable=False)

    def __str__(self):
        return f"{self.name}"

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
        return Mandat.objects.filter(
            expiration_date__gte=timezone.now(), organisation=self
        ).count()

    @cached_property
    def aidants_not_responsables(self):
        return self.aidants.exclude(responsable_de=self).all()

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
            if len(aidant.organisations.all()) == 1:
                aidant.is_active = False
                aidant.save()
            else:
                aidant.organisations.remove(self)
                if aidant.organisation not in aidant.organisations.all():
                    aidant.organisation = aidant.organisations.first()
                aidant.save()

    def activate_organisation(self):
        self.is_active = True
        self.save()


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


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
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

    objects = AidantManager()

    REQUIRED_FIELDS = AbstractUser.REQUIRED_FIELDS + ["organisation"]

    class Meta:
        verbose_name = "aidant"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

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
        try:
            TOTPDevice.objects.get(user=self, confirmed=True)
            return True
        except TOTPDevice.MultipleObjectsReturned:
            return True
        except TOTPDevice.DoesNotExist:
            return False

    @cached_property
    def has_a_carte_totp(self):
        try:
            CarteTOTP.objects.get(aidant=self)
            return True
        except CarteTOTP.DoesNotExist:
            return False

    def remove_user_from_organisation(
        self, organisation: Organisation
    ) -> Optional[bool]:
        if self.organisations.filter(pk=organisation.id).count() == 0:
            return None

        if self.organisations.count() == 1:
            self.is_active = False
            self.save()

            return self.is_active

        self.organisations.remove(self.organisation)
        if self.organisations.filter(pk=self.organisation.id).count() == 0:
            self.organisation = self.organisations.first()
            self.save()

        return self.is_active


class HabilitationRequest(models.Model):
    STATUS_NEW = "new"
    STATUS_PROCESSING = "processing"
    STATUS_VALIDATED = "validated"
    STATUS_REFUSED = "refused"
    STATUS_CANCELLED = "cancelled"

    ORIGIN_DATAPASS = "datapass"
    ORIGIN_RESPONSABLE = "responsable"
    ORIGIN_OTHER = "autre"

    STATUS_LABELS = {
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
        default=STATUS_NEW,
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

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("email", "organisation"), name="unique_email_per_orga"
            ),
        )
        verbose_name = "demande d’habilitation"
        verbose_name_plural = "demandes d’habilitation"

    def __str__(self):
        return f"{self.email}"

    def validate_and_create_aidant(self):
        if self.status != self.STATUS_PROCESSING:
            return False

        if Aidant.objects.filter(username=self.email).count() > 0:
            aidant = Aidant.objects.get(username=self.email)
            aidant.organisations.add(self.organisation)
            self.status = self.STATUS_VALIDATED
            self.save()
            return True

        aidant = Aidant(
            last_name=self.last_name,
            first_name=self.first_name,
            profession=self.profession,
            organisation=self.organisation,
            email=self.email,
            username=self.email,
        )
        self.status = self.STATUS_VALIDATED
        aidant.save()
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


def get_staff_organisation_name_id() -> int:
    try:
        return Organisation.objects.get(name=settings.STAFF_ORGANISATION_NAME).pk
    except Organisation.DoesNotExist:
        return 1


class MandatQuerySet(models.QuerySet):
    def active(self):
        return (
            self.exclude(expiration_date__lt=timezone.now())
            .filter(autorisations__revocation_date__isnull=True)
            .distinct()
        )

    def inactive(self):
        return self.filter(
            Q(expiration_date__lt=timezone.now())
            | ~Q(autorisations__revocation_date__isnull=True)
        ).distinct()


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
    is_remote = models.BooleanField("Signé à distance ?", default=False)

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

    @cached_property
    def revocation_date(self) -> Optional[datetime]:
        """
        Returns the date of the most recently revoked authorization if all them
        were revoked, ``None``, otherwise.
        """
        return (
            self.autorisations.order_by("-revocation_date").first().revocation_date
            if self.was_explicitly_revoked
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

    def get_mandate_template_path(self) -> Union[None, str]:
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
    def get_attestation_hash_or_none(cls, mandate_id):
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
        max_length=16, choices=AuthorizationDurationChoices.choices, null=True
    )
    mandat_is_remote = models.BooleanField(default=False)
    user_phone = PhoneNumberField(blank=True)

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

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(aidant__isnull=True) & Q(organisation__isnull=True))
                    | (Q(aidant__isnull=False) & Q(organisation__isnull=False))
                ),
                name="aidant_and_organisation_set_together",
            )
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
    mandat = models.ForeignKey(
        Mandat, null=True, on_delete=models.PROTECT, related_name="journal_entries"
    )

    organisation = models.ForeignKey(
        Organisation, on_delete=models.PROTECT, related_name="journal_entries"
    )

    objects = JournalQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée de journal"
        verbose_name_plural = "entrées de journal"

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
    ):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.INIT_RENEW_MANDAT,
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            is_remote_mandat=is_remote_mandat,
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
    ):
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


class CarteTOTP(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    seed = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    aidant = models.OneToOneField(
        Aidant, null=True, blank=True, on_delete=SET_NULL, related_name="carte_totp"
    )

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


# The Dataviz* models represent metadata that are used for data display in Metabase.
# Do not remove even if they are not used directly in the code.
class DatavizDepartment(models.Model):
    zipcode = models.CharField(
        "Code Postal", max_length=10, null=False, blank=False, unique=True
    )
    dep_name = models.CharField(
        "Nom de département", max_length=50, null=False, blank=False
    )

    class Meta:
        db_table = "dataviz_department"
        verbose_name = "Département"


class DatavizRegion(models.Model):
    name = models.CharField(
        "Nom de région", max_length=50, null=False, blank=False, unique=True
    )

    class Meta:
        db_table = "dataviz_region"
        verbose_name = "Région"


class DatavizDepartmentsToRegion(models.Model):
    department = models.OneToOneField(
        DatavizDepartment,
        null=False,
        blank=False,
        on_delete=CASCADE,
    )
    region = models.ForeignKey(
        DatavizRegion, null=False, blank=False, on_delete=CASCADE
    )

    class Meta:
        db_table = "dataviz_departements_to_region"
        verbose_name = "Assocation départments/région"
        verbose_name_plural = "Assocations départments/région"
